# Agent Skills

[![skills.sh](https://skills.sh/b/tarikrazine/skills)](https://skills.sh/tarikrazine/skills)

Reusable skills for AI coding agents (Claude Code, Cursor, Codex, and any
[agentskills.io](https://agentskills.io)-compatible agent).

## Skills

| Skill | Description | Install |
|---|---|---|
| [competitor-homepage-watch](skills/competitor-homepage-watch/SKILL.md) | Daily competitive intelligence from competitor homepages: crawl, diff vs yesterday, alert on new/ended promos, archive into a commercial-plan calendar with screenshots. | `npx skills add tarikrazine/skills --skill competitor-homepage-watch` |
| [xquik-x-data](skills/xquik-x-data/SKILL.md) | Source-backed Xquik REST API and MCP workflow planning for public X data integrations. | `npx skills add tarikrazine/skills --skill xquik-x-data` |

## Usage

```bash
# install a skill into the current project (any agentskills.io-compatible agent)
npx skills add tarikrazine/skills --skill competitor-homepage-watch
npx skills add tarikrazine/skills --skill xquik-x-data
```

Or as a Claude Code plugin marketplace:

```
/plugin marketplace add tarikrazine/skills
/plugin install competitor-homepage-watch@tarikrazine-skills
```

Skill scripts are Python 3 standard library only - no pip dependencies.
`competitor-homepage-watch` optionally uses a [Firecrawl](https://firecrawl.dev)
API key (`FIRECRAWL_API_KEY`) for JavaScript rendering and screenshots, with a
plain-HTTP fallback when no key is set.

## License

MIT
