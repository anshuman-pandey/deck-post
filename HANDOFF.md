# Deck Post local preview

An open-source alternative for DocSend's PDF-sharing workflow: immutable PDF uploads, private links with expiry and revocation, and download-request counts. MIT licensed; no public repository, release or hosted demo claimed.

## Run

```sh
python3 scripts/setup.py
docker compose up --build -d
```

Read the private `.env` locally for the owner key. Open http://127.0.0.1:8099, unlock, upload a PDF and select it. Set an expiry in your local time, create a private link and save it. Open the link in another tab to download; refresh the owner view to see requests, then revoke access and verify another download is denied. Localhost links work only on the same computer; remote sharing requires HTTPS hosting and validation.

English, German, Spanish, Japanese, Simplified Chinese and Traditional Chinese are included. Switching language preserves selected files, expiry values, private links and original filenames. Native browser controls follow browser settings. Native-speaker review remains pending.

Counts mean authorized retrieval requests, not completed downloads, unique people or proof of reading. Revocation cannot recall saved copies or stop a transfer already authorized. PDF validation checks structure, not malware. No identity verification, signatures, page analytics, download prevention or full DocSend parity is claimed.

See [deployment and recovery](docs/DEPLOYMENT.md), [validation evidence](artifacts/validation.json) and [scope/source references](docs/SCOPE.md).

## Publication handoff

[Prefilled GitHub form](https://github.com/new?name=deck-post&description=Open-source%20alternative%20to%20DocSend%20for%20PDF%20sharing.%20Private%20expiring%20links%2C%20revocation%20and%20download-request%20counts.%20Self-hosted%2C%20six%20languages%2C%20MIT%20licensed.&visibility=public)

Create an empty repository under anshuman-pandey and give the product-specific go-ahead to push. Existing remote contents will be inspected before publication. The provisional name still needs owner review. Source publication is separate from a tested release or hosted demo.
