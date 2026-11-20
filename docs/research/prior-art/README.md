# Prior art

Repos we evaluated and the ideas worth taking from each. **We take ideas, not code.** Write everything here in our own words, with a link to the source. Copy nothing:

| Repo | Licence | Can we copy code? |
|---|---|---|
| [Matt28296/3D-Printing-Agent-Network](https://github.com/Matt28296/3D-Printing-Agent-Network/tree/f2276a6eb96077cee03177cffcc953106022efe2) | None (all rights reserved) | No |
| [brs077/3dp-mcp-server](https://github.com/brs077/3dp-mcp-server/tree/960e8de46fc52b82939bc43619cb16a7d4897374) | CC BY-NC-ND 4.0 | No (modified versions not allowed) |
| [pzfreo/build123d-mcp](https://github.com/pzfreo/build123d-mcp/tree/4aaafe2151bcb2e5f51a0951e4b5357b888e6c2b) | Apache-2.0 | Yes, with attribution. We use it as a dependency instead. |
| [KvashaIhor/print-studio](https://github.com/KvashaIhor/print-studio/tree/bda70052d8d9494ff5cec1d5b4eee3e3735eba33) | MIT | Yes, with attribution. We take ideas only. |

Each repo was checked from four angles on 2026-11-15:
- **Run:** install it, run its tests and drive its tools.
- **Code review.**
- **Fact-check** against primary sources.
- **Provenance:** where it came from and whether it holds together.

All links are pinned to the commit that was reviewed.

- [mk3-agent-network.md](mk3-agent-network.md): the most ideas, worth copying in spirit
- [build123d-mcp.md](build123d-mcp.md): our CAD engine
- [3dp-mcp-server.md](3dp-mcp-server.md): mostly a list of things not to trust
- [print-studio.md](print-studio.md): printability checks, inspection views and a fit record to take; reviewed 2026-11-20 without running it
