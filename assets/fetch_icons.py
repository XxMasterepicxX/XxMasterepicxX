"""Downloads brand icon paths + colors into assets/icons.json. Run only when adding icons."""
import json, re, io, urllib.request

SLUGS = {
    "C#": "csharp", "TypeScript": "typescript", "JavaScript": "javascript", "Python": "python",
    "C++": "cplusplus", "Java": "openjdk",
    ".NET": "dotnet", "React": "react", "Node": "nodedotjs", "Fastify": "fastify",
    "FastAPI": "fastapi", "Django": "django", "Electron": "electron", "Vite": "vite",
    "Tailwind": "tailwindcss", "Prisma": "prisma",
    "PostgreSQL": "postgresql", "SQLite": "sqlite", "AWS": "amazonwebservices",
    "BigQuery": "googlebigquery", "Firebase": "firebase", "Docker": "docker",
    "PyTorch": "pytorch", "scikit-learn": "scikitlearn", "ONNX": "onnx",
    "Actions": "githubactions", "Linux": "linux",
}
# the color CDN is versioned separately and is missing a few of these slugs
FALLBACK_HEX = {"csharp": "#9B4F96", "amazonwebservices": "#FF9900"}
UA = {"User-Agent": "readme-build-script"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read().decode()

out = {}
for name, slug in SLUGS.items():
    d = re.search(r'<path d="([^"]+)"',
                  get(f"https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg"))
    hexv = FALLBACK_HEX.get(slug)
    if not hexv:
        m = re.search(r'fill="(#[0-9A-Fa-f]{6})"', get(f"https://cdn.simpleicons.org/{slug}"))
        hexv = m.group(1) if m else "#8B949E"
    out[name] = {"hex": hexv, "d": d.group(1)}
    print(f"{name:14} {hexv}")

io.open("assets/icons.json", "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=1))
print("wrote", len(out), "icons")
