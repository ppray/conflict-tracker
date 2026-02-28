# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a single-file HTML application - a Middle East conflict tracker (中东战况实时播报系统) that displays real-time military events on an interactive map with a scrolling event feed. It's a demo/prototype application with mock data.

## Architecture

The entire application is contained in `conflict-tracker.html` with three main sections:

1. **CSS Styles** (inline in `<style>`) - Military/radar-themed UI with scan line overlays, CRT effects, and green/amber/red color scheme
2. **HTML Structure** - Header, main map panel, events panel, and footer ticker
3. **JavaScript** (inline in `<script>`) - All application logic

### Key JavaScript Components

- **MOCK_EVENTS** - Array of conflict event objects with properties: `id`, `type` (strike/blockade/airspace/intel), `country`, `title`, `desc`, `location` [lat, lng], `locationName`, `time`, `source`, `isNew`
- **Leaflet Map** - Centered on Middle East (28.0°N, 43.0°E), zoom 5, using OpenStreetMap tiles with dark filter
- **Markers** - Custom divIcon with pulse animations, symbols by type (✕ strike, ⊘ blockade, △ airspace, ◆ intel)
- **Event List** - Filterable by country or type, with stats bar showing counts
- **Auto-refresh** - Simulates new events every 30 seconds using NEW_EVENT_TEMPLATES

### Event Types & Styling

| Type | Badge Color | Symbol | CSS Class |
|------|-------------|--------|-----------|
| strike | red (#ff3344) | ✕ | `.badge-strike`, `.type-strike` |
| blockade | amber (#ffaa00) | ⊘ | `.badge-blockade`, `.type-blockade` |
| airspace | blue (#00aaff) | △ | `.badge-airspace`, `.type-airspace` |
| intel | green (#00ff88) | ◆ | `.badge-intel`, `.type-intel` |
| diplomatic | white (#c8e4f0) | ● | `.badge-diplomatic` |

## Running the Application

Simply open `conflict-tracker.html` in a web browser. No build process or dependencies required - it loads Leaflet and fonts from CDNs.

```bash
# Serve locally (optional, for development)
python3 -m http.server 8000
# Then open http://localhost:8000/conflict-tracker.html
```

## Modifying the Application

- **Add new event types**: Update `typeIcons` object, add CSS badge classes, and update `getBadgeText()` function
- **Change map region**: Modify `map` initialization center coordinates and zoom level
- **Add map overlays**: Use Leaflet methods like `L.polyline()`, `L.polygon()` - see `hormuzLine`, `redSeaZone`, `pgZone` examples
- **Customize refresh interval**: Change `setInterval(performRefresh, 30000)` timing in `startAutoRefresh()`
- **Modify mock data**: Edit `MOCK_EVENTS` array or `NEW_EVENT_TEMPLATES` for simulated events

## CSS Custom Properties (Theming)

Key colors defined in `:root`:
- `--accent-green`: Primary accent (#00ff88)
- `--accent-amber`: Warning color (#ffaa00)
- `--accent-red`: Danger color (#ff3344)
- `--accent-blue`: Info color (#00aaff)
- `--bg-primary` through `--bg-card`: Background hierarchy

## External Dependencies

- Leaflet 1.9.4 (CSS + JS) - via cdnjs.cloudflare.com
- Google Fonts - 'Share Tech Mono', 'Rajdhani'
