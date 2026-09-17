import { api, ApiError, parseError } from "../lib/api";

afterEach(() => vi.restoreAllMocks());

it("parses the backend error envelope", async () => {
  const response = new Response(JSON.stringify({ error: { code: "PROJECT_EXISTS", message: "Already registered.", project_id: 3 } }), { status: 409 });
  const err = await parseError(response);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.code).toBe("PROJECT_EXISTS");
  expect(err.extra.project_id).toBe(3);
});

it("falls back when the error body is not JSON", async () => {
  const err = await parseError(new Response("<html>", { status: 502 }));
  expect(err.code).toBe("HTTP_ERROR");
  expect(err.status).toBe(502);
});

it("turns network failures into a readable error", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
  await expect(api.listProjects()).rejects.toMatchObject({ code: "NETWORK_ERROR" });
});

it("posts the repository URL as JSON", async () => {
  const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: 1 }), { status: 201 }));
  await api.createProject("https://github.com/a/b");
  expect(spy).toHaveBeenCalledWith("/api/projects", expect.objectContaining({ method: "POST", body: JSON.stringify({ repository_url: "https://github.com/a/b" }) }));
});
