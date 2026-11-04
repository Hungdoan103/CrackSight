Darwin 3D (Cesium Photoreal)
=============================
1. Create a Cesium ion account: https://ion.cesium.com
2. Enable Google Photorealistic 3D Tiles for the account
3. Copy an access token into frontend/.env.local:

   NEXT_PUBLIC_CESIUM_ION_TOKEN=eyJ...

4. Restart `npm run dev`
5. Open http://127.0.0.1:3000/darwin

Without a token the page falls back to Esri World Imagery + terrain.
Vehicles and streetlights are simulated along Darwin CBD corridors.
