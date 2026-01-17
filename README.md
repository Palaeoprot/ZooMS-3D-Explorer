# ZooMS Interactive Explorer
Interactive 3D visualization of ZooMS data.

[Launch Dashboard](https://palaeoprot.github.io/ZooMS-3D-Explorer/)

## Codicum Archival Sync
This repository includes an automated workflow for synchronizing archaeological parchment images from Google Drive to the 3D Explorer.

### Key Tools
- **`sync_parchment_data.py`**: The main synchronization script. It handles batch processing of ZIP files, QR code identification, thumbnail generation, and Google Sheets logging.
- **Deduplication**: Automatically cleans and shrinks ZIP files on Google Drive to save storage.
- **Metadata Tracking**: Captures "Creator" information and generates live image previews in a Google Sheets tracking log.

### Documentation
- [Codicum Sync Guide](DOCUMENTATION/CODICUM_SYNC_GUIDE.md): A non-technical guide for running the archival workflow.
- [Technical Documentation](DOCUMENTATION/CODICUM_SYNC_DOCUMENTATION.md): Detailed technical overview of the system architecture.

### Setup
Ensure you have `credentials.json` in the root directory and run:
```bash
pip install -r requirements.txt
python3 sync_parchment_data.py
```
