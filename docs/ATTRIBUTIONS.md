# Moniq dependencies and acknowledgments

The application includes no copied third-party hackathon project or proprietary business code. All student/demo/offer/training data was generated for this project; see `data/LICENSE.md`. Merchant and Georgia State University names are descriptive references, with no affiliation or live-offer claim.

| Primary dependency | License / source |
| --- | --- |
| React / React DOM | MIT — https://github.com/facebook/react |
| TypeScript | Apache-2.0 — https://github.com/microsoft/TypeScript |
| Vite | MIT — https://github.com/vitejs/vite |
| Tailwind CSS | MIT — https://github.com/tailwindlabs/tailwindcss |
| Recharts | MIT — https://github.com/recharts/recharts |
| Lucide | ISC — https://github.com/lucide-icons/lucide |
| Python | PSF — https://www.python.org/psf/license/ |
| FastAPI | MIT — https://github.com/fastapi/fastapi |
| Uvicorn | BSD-3-Clause — https://github.com/encode/uvicorn |
| SQLAlchemy | MIT — https://github.com/sqlalchemy/sqlalchemy |
| SQLite | Public domain — https://www.sqlite.org/copyright.html |
| pandas | BSD-3-Clause — https://github.com/pandas-dev/pandas |
| scikit-learn | BSD-3-Clause — https://github.com/scikit-learn/scikit-learn |
| joblib | BSD-3-Clause — https://github.com/joblib/joblib |
| pytest | MIT — https://github.com/pytest-dev/pytest |
| Ruff | MIT — https://github.com/astral-sh/ruff |
| ESLint | MIT — https://github.com/eslint/eslint |
| Playwright | Apache-2.0 — https://github.com/microsoft/playwright |

Exact installed backend versions and transitive packages are recorded in `backend/requirements-lock.txt`; frontend resolutions are in `frontend/package-lock.json`. Their installed distributions retain individual license/notice files. No framework distribution license was replaced. Review any added assets/packages before publication. The authors' source-code license has not been chosen; the team must select an appropriate repository license if desired before publishing.

OpenAI Codex assisted generation, integration, tests, debugging, and documentation. No paid external API runs in the app. Local Node.js and Python are development tools, excluded from Git. No Gemini/Plaid sponsor usage is claimed.

The Moniq Circles and SmartApprove upgrade adds original application code and layouts using existing dependencies; no competing product source, branding, artwork, or payment SDK was added. Gmail OAuth dependencies added locally: Authlib (BSD-3-Clause), cryptography (Apache-2.0/BSD-3-Clause), joserfc (BSD-3-Clause), cffi (MIT), and pycparser (BSD-3-Clause); exact versions and distribution notices remain in the lockfile and installed packages.

Final media is original screen capture of Moniq synthetic workspaces. Playwright/Chromium records actual UI; imageio-ffmpeg 0.6.0 (BSD-2-Clause) supplies a locally installed FFmpeg 7.1 executable (FFmpeg licensing depends on its compiled components; binary/dependency tools are not redistributed). MP4 encoding uses libx264. Narration uses the installed Microsoft Zira Desktop Windows voice. No music, third-party stock footage or personal emails appear. Codex assisted media scripting and production.

The new premium edit uses fresh `en-US-AndrewMultilingualNeural` American narration through Microsoft Edge's online speech service, using edge-tts 7.2.3 (LGPLv3 client; https://github.com/rany2/edge-tts). The client and its installed notices remain in ignored `.tools/neural-tts`; neither the client distribution nor service credentials are bundled in the application. Only synthetic product narration is sent to the service. Andrew is identified by the service as neural, confident, casual and warm. Voice synthesis uses +15% rate and brand pronunciation text; captions use the official brand spellings. No music or paid API key is used. The preserved earlier videos retain their original Windows voices.

PWA build support uses vite-plugin-pwa and Workbox; their versions/notices remain in the frontend lockfile and installed packages. The app icons are rasterizations of Moniq's existing original vector icon, with an inset maskable variant; no external brand artwork was added.
