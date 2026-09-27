import httpx
import pytest

from app.services.github_client import (
    GitHubClient,
    GitHubError,
    GitHubUnavailable,
    InvalidRepositoryURL,
    RateLimited,
    RepositoryNotFound,
    parse_repo_url,
)


@pytest.mark.parametrize("url,expected", [
    ("https://github.com/pallets/flask", ("pallets", "flask")),
    ("http://www.github.com/pallets/flask/", ("pallets", "flask")),
    ("https://github.com/owner-1/repo.name_x.git", ("owner-1", "repo.name_x")),
    ("pallets/flask", ("pallets", "flask")),
])
def test_parse_valid_urls(url, expected):
    assert parse_repo_url(url) == expected


@pytest.mark.parametrize("url", [
    "", "https://gitlab.com/a/b", "https://github.com/onlyowner", "https://github.com/a/b/issues",
    "https://github.com/../etc", "javascript:alert(1)", "https://github.com/-bad/repo",
    "https://github.com/a/b; DROP TABLE projects;--", "https://github.com/" + "a" * 400 + "/b",
    "https://evil.com/github.com/a/b",
])
def test_parse_invalid_urls(url):
    with pytest.raises(InvalidRepositoryURL):
        parse_repo_url(url)


def make_client(handler, token="tkn"):
    return GitHubClient(token=token, transport=httpx.MockTransport(handler), sleep=lambda _: None)


def test_pagination_follows_link_header_and_caps_pages():
    def handler(request):
        page = int(request.url.params.get("page", 1))
        headers = {"link": f'<https://api.github.com/items?page={page + 1}&per_page=100>; rel="next"'}
        return httpx.Response(200, headers=headers, json=[{"n": page}])

    client = make_client(handler)
    result = client.paginate("/items", max_pages=3)
    assert [i["n"] for i in result.items] == [1, 2, 3]
    assert result.truncated is True
    assert client.calls == 3


def test_pagination_stop_predicate():
    client = make_client(lambda r: httpx.Response(200, json=[{"n": 1}, {"n": 2}, {"n": 3}]))
    result = client.paginate("/items", stop=lambda item: item["n"] == 2)
    assert result.items == [{"n": 1}] and result.truncated is False


def test_rate_limit_raises_with_reset_time():
    client = make_client(lambda r: httpx.Response(
        403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1900000000"},
        json={"message": "API rate limit exceeded"}), token=None)
    with pytest.raises(RateLimited) as err:
        client.get_repository("a", "b")
    assert err.value.extra["reset_at"].startswith("2030")
    assert "GITHUB_TOKEN" in err.value.message


def test_secondary_rate_limit_429():
    with pytest.raises(RateLimited):
        make_client(lambda r: httpx.Response(429, json={})).get_repository("a", "b")


def test_not_found():
    with pytest.raises(RepositoryNotFound):
        make_client(lambda r: httpx.Response(404, json={})).get_repository("a", "b")


def test_bad_token_401():
    with pytest.raises(GitHubError, match="401"):
        make_client(lambda r: httpx.Response(401, json={})).get_repository("a", "b")


def test_server_error_is_retried_then_succeeds():
    responses = iter([httpx.Response(502), httpx.Response(200, json={"full_name": "a/b"})])
    client = make_client(lambda r: next(responses))
    assert client.get_repository("a", "b")["full_name"] == "a/b"
    assert client.calls == 2


def test_server_error_exhausts_retries():
    client = make_client(lambda r: httpx.Response(503))
    with pytest.raises(GitHubUnavailable):
        client.get_repository("a", "b")
    assert client.calls == 3


def test_network_failure_becomes_unavailable():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(GitHubUnavailable):
        make_client(handler).get_repository("a", "b")


def test_empty_repository_409_returns_no_commits():
    result = make_client(lambda r: httpx.Response(409, json={})).paginate("/repos/a/b/commits")
    assert result.items == [] and not result.truncated


def test_token_sent_as_bearer_header():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={})

    make_client(handler, token="abc").get_repository("a", "b")
    assert seen["auth"] == "Bearer abc"
