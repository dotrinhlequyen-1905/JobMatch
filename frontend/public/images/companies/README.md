# Employer avatars

`catalog.json` maps normalized employer names to local WebP logos. Each logo keeps
its recruitment profile or official website in `source_url`, and its original
image in `image_url`. The TechPlus logo comes from https://vi.techplus.vn/.
The images identify the respective employers; JobMatch does not claim ownership
of their trademarks.

The importer reads `company_image_url` from the original recruitment CSV,
validates each bitmap, excludes platform defaults and bounds its dimensions to
320 px. Expired ITviec images are recovered from an identified employer profile
where possible. Names that have no usable source use `company-placeholder.svg`.
This shared illustration is not an official employer logo.

Refresh the local catalog from the repository root (requires Pillow):

```powershell
.venv\Scripts\python.exe scripts/import_company_logos.py
```

Preview and fill empty avatar fields in an existing database:

```powershell
.venv\Scripts\python.exe backend/scripts/sync_company_logos.py
.venv\Scripts\python.exe backend/scripts/sync_company_logos.py --apply
```

The sync only fills blank logo URLs. Employer supplied images remain preferred.
The frontend falls back to the local catalog and illustration if an image fails.
New demo seeds also use this catalog, without changing the research dataset.
