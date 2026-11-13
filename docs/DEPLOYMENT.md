# Publish the Streamlit app

Status: **not deployed**. A working public link is still required before submitting PD2.

1. Create/sign in to GitHub and create a repository called `stock-strategy-lab` (or a chosen name). Do not upload `.venv`, caches, local databases or secrets.
2. Upload this folder's source files so `app.py` and `requirements.txt` are at the repository root. Include `engine.py`, `data_source.py`, `storage.py` and `.streamlit/config.toml`.
3. Sign in to <https://share.streamlit.io/> using GitHub and authorize the chosen repository.
4. Choose **Create app**, select your repository and branch, set main file to `app.py`, and select **Python 3.12** in advanced settings. Deploy.
5. Use the **actual assigned URL** shown after deployment. Open it in a fresh browser. Confirm the demo has four metrics, plots and strategy comparisons, and that save/restore works within the session.
6. Try Yahoo with `MSFT` first. A provider error should be visible; never claim market integration passed if only the synthetic demo worked. Then try three USD symbols. Do not exceed 20.
7. Download metrics, trades and JSON, and check their contents. Test a second browser session to confirm it cannot see the first session's SQLite records.
8. Replace the pending cloud URL in the Word report with the verified public URL. Submit the Word file, project ZIP and that link to Moodle.

Cloud-local SQLite is temporary and has not been load-tested. For an ongoing service, use authenticated accounts and managed persistent storage before retaining financial information. Do not put API keys in the repository. Yahoo access is subject to provider availability and terms.

Official deployment guide: <https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app>
