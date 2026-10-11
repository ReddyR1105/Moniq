# Native Moniq roadmap — not an APK delivery

Preserve the existing React/TypeScript application. The immediate mobile deliverable is the PWA; no Capacitor branch, native project, APK, signed app or App Store submission has been created. Per the owner's sequencing request, native work begins only after public hosting and hackathon submission are finished, with sufficient remaining time.

This Windows workspace has Android Studio, SDK platforms, platform-tools/ADB, command-line SDK tools and a bundled Java runtime. That establishes available tooling, not a successful Gradle build. A compatible Studio/Gradle/JDK combination must be checked when development begins.

## Future separate branch

```powershell
git switch -c mobile/capacitor
cd frontend
npm install @capacitor/core@8 @capacitor/android@8
npm install --save-dev @capacitor/cli@8
npx cap init Moniq com.moniq.app --web-dir dist
npm run build
npx cap add android
npx cap sync android
npx cap open android
```

These are proposed commands, not executed results. Confirm package versions against the [official Capacitor environment requirements](https://capacitorjs.com/docs/getting-started/environment-setup) when starting. Capacitor 8 requires Node 22+; this project uses Node 24. Build a debug APK with the generated Gradle wrapper only after the Android project and API integration work; signing/distribution is a separate step.

## API integration is required

The current React client uses same-origin `/api` and browser session cookies. A bundled Capacitor WebView has a different origin. Merely running `cap add android` does not connect the backend. Implement explicit HTTPS API configuration, native-origin validation and session handling before claiming the wrapper works. Never expose the owner's loopback Gmail backend, weaken public sample-only restrictions or copy `.env`/tokens into a bundle. The native public demo must remain synthetic; real user hosting requires authenticated accounts and a separate privacy/security design. Native Gmail would require an appropriate external browser consent flow and registered callbacks; the existing local web callback is not a native OAuth implementation.

## iOS

iOS builds require a Mac, a supported Xcode installation, signing and an Apple development setup. This Windows workspace cannot produce a verified iOS build. Consult current Capacitor requirements before adding the iOS platform. No App Store or Play Store account, purchase or publication is authorized.
