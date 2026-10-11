# Public demo preparation and approval boundary

The existing app has been prepared locally for one Render Docker web service serving both FastAPI `/api` and the Vite production frontend on the same HTTPS origin. `render.yaml` selects **Free**, one instance and manual deployments. Gmail credentials are disabled unconditionally in public mode; private/scenario database helpers reject public access rather than falling back to owner data. Public writes require the service origin, responses have no-store headers, and static delivery has a same-origin CSP. The local owner's Gmail connection and databases are preserved.

No new GitHub push, Render deployment, DNS change, public media upload or Devpost submission has occurred. There is no verified live application URL. Container tooling is unavailable, so a Docker image build and real Render startup remain unverified. The equivalent production frontend/backend path passes local automated browser checks. See `DEPLOYMENT.md` for the proposed deployment and `MOBILE_SETUP.md` for phone instructions.

## Costs to review before approval

- Render Free provides a temporary demonstration service, not guaranteed uptime or durable storage. It sleeps after 15 idle minutes and may take about a minute to wake. Workspace free-hour and other usage limits apply. [Official free-service limits](https://render.com/docs/free).
- Free compute does not establish that every account can never be billed. With a payment method, supplementary bandwidth or pipeline usage may incur charges. Use an account without a payment method for the strict no-charge path, or have the owner verify all account limits before approval. A pipeline spending cap alone does not cap every billing category. [Build pipeline limits](https://render.com/docs/build-pipeline).
- An always-on Starter service is a proposed paid alternative at $7/month before other usage charges, requiring separate explicit approval. No paid plan, disk, subscription or purchase has been selected. [Render's published plan comparison](https://render.com/articles/render-vs-railway).

## Exact external actions still requiring approval

1. Publish the verified local source changes to the existing `ReddyR1105/Moniq` repository, without force-push, after reviewing the final diff and checking remote history.
2. Authenticate the owner's Render account, create one **Free** Docker service from the approved main branch using root `render.yaml`, and trigger its deployment. Do not add a paid disk, paid instance, custom domain or Gmail credentials.
3. Inspect build/start logs, verify `/api/health` and real HTTPS, then test independent visitors, public restrictions, reset and PWA/mobile behavior on the actual external URL. Only then enter the verified URL into submission materials.

The connected tools do not provide a Render account-management integration in this session. Account authentication and service creation therefore require the owner or an explicitly approved supported interface; no account credentials should be pasted into chat.

After an approved deployment, the external test command is:

```powershell
$env:MONIQ_PUBLIC_BASE_URL='https://<actual-verified-service-host>'
npm --prefix frontend run test:deployed
```

This command is prepared, not run. It refuses a non-HTTPS or credential-bearing origin and uses the actual service without starting a local substitute. Hosting, video upload and Devpost submission remain distinct approval steps.
