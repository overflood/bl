# Borderliner.ch Hugo Site

Dieses Repository enthält die statische Website für **borderliner.ch**. Die Seiten basieren auf den Inhalten der früheren Domain `blz.borderliner.ch` und wurden in ein modernes Hugo‑Projekt überführt.

## Inhalt und Struktur

* Der Ordner `content/` enthält alle Artikel als Markdown‑Dateien mit YAML‑Front‑Matter. Hier sind Titel, Datum, Kategorien, Slug und Aliases hinterlegt. Die `aliases` verweist auf die ursprünglichen HTML‑Pfade, sodass Weiterleitungen eingerichtet werden können.
* Der Ordner `static/` enthält alle Bilder, Skripte und sonstigen Assets. Zusätzlich befindet sich hier die Datei `_redirects`, die alte Pfade auf die neuen Slugs umleitet (Netlify‑/Cloudflare‑Syntax).
* Die Datei `config.toml` definiert grundlegende Parameter wie Titel, Sprache, Menü und das verwendete Theme.
* In `.github/workflows/build-and-deploy.yml` ist eine GitHub‑Action hinterlegt, die bei jedem Commit die Seite mit Hugo baut und auf die `gh-pages`‑Branch (GitHub Pages) veröffentlicht.

## Lokales Bauen

Um die Seite lokal zu bauen, benötigst du [Hugo](https://gohugo.io/). Installiere es mit dem Extended‑Build (für SCSS‑Support) und führe dann im Repository‐Verzeichnis Folgendes aus:

```bash
hugo server --buildDrafts --buildFuture
```

Die Seite ist anschließend unter `http://localhost:1313` verfügbar. Änderungen an den Markdown‑Dateien werden automatisch neu gebaut.

## Deployment

Die Bereitstellung erfolgt automatisch über GitHub Pages. Jede Änderung an der `main`‑Branch stößt den Build‑Workflow an. Die statische Ausgabe (`public/`) wird auf die `gh-pages`‑Branch gepusht und von GitHub Pages ausgeliefert.

## Migration der Inhalte

Die alten HTML‑Seiten wurden mithilfe eines Python‑Skripts nach Markdown konvertiert. Das Skript extrahiert Titel, Datum aus der Sitemap und kategorisiert die Seiten anhand der Verzeichnisstruktur. Anker und interne Links wurden in Markdown umgewandelt.

Sollten weitere alte Seiten auftauchen oder neue Beiträge erstellt werden, kann das Skript erneut ausgeführt oder entsprechend angepasst werden. Neue Inhalte können einfach als Markdown‑Dateien in `content/` abgelegt werden.
