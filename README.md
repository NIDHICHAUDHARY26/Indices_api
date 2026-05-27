
  REMOTE SENSING MCP — WINDOWS SETUP GUIDE
  Project: amnex1-487305 | Krishi DSS


STEP 1 — COPY PROJECT FILES
─────────────────────────────
Copy the entire "remote_sensing_mcp" folder to:
  C:\Amnex-Learning\march_task\indices_mcp\remote_sensing_mcp\

Your folder structure should look like:
  C:\Amnex-Learning\march_task\indices_mcp\
  ├── amne.......json       ← your service account key
  ├── SOI - SUBDISTRICT\taluka\taluka.shp   ← your shapefile
  └── remote_sensing_mcp\                   ← THIS project folder
      ├── server.py
      ├── config.py
      ├── requirements.txt
      ├── tools\
      └── utils\


STEP 2 — ENABLE EARTH ENGINE API IN GCP
─────────────────────────────────────────
1. Go to: https://console.cloud.google.com/apis/library
2. Make sure project "amnex1-487305" is selected (top bar)
3. Search for "Earth Engine API"
4. Click ENABLE


STEP 3 — REGISTER SERVICE ACCOUNT IN GEE
──────────────────────────────────────────
1. Go to: https://code.earthengine.google.com/register
2. Click "Register a noncommercial or commercial Cloud project"
3. Choose "Use with an existing Google Cloud Project"
4. Enter project ID: 
5. Complete registration

Then register your service account:
1. Go to: https://signup.earthengine.google.com/#!/service_accounts
   OR run in Python after install:
   earthengine authenticate --service_account_file=


STEP 4 — INSTALL PYTHON DEPENDENCIES
──────────────────────────────────────
Open Command Prompt (cmd) as Administrator:

  cd C:\Amnex-Learning\march_task\indices_mcp\remote_sensing_mcp
  pip install -r requirements.txt

If you get GDAL errors with geopandas, install via conda:
  conda install -c conda-forge geopandas


STEP 5 — TEST THE SERVER
──────────────────────────
In Command Prompt:
  cd C:\Amnex-Learning\march_task\indices_mcp\remote_sensing_mcp
  python server.py

You should see:
  🛰️  Remote Sensing MCP Server starting...
  📂 Loading taluka boundaries...
  ✅ Loaded 6314 talukas from shapefile
  🌍 GEE will initialize on first index query
  ✅ MCP Server ready. Waiting for Claude...

Press Ctrl+C to stop the test.


STEP 6 — CONFIGURE CLAUDE DESKTOP
────────────────────────────────────
1. Install Claude Desktop from: https://claude.ai/download
2. Open Claude Desktop
3. Go to: Settings → Developer → Edit Config
   OR open this file directly:
   C:\Users\<YourUsername>\AppData\Roaming\Claude\claude_desktop_config.json

4. REPLACE the entire file content with the contents of:
   claude_desktop_config.json (in this project folder)

   It looks like this:
   {
     "mcpServers": {
       "remote-sensing": {
         "command": "python",
         "args": [
           "C:\\Amnex-Learning\\march_task\\indices_mcp\\remote_sensing_mcp\\server.py"
         ]
       }
     }
   }

5. SAVE the file
6. RESTART Claude Desktop completely


STEP 7 — TEST IN CLAUDE DESKTOP
──────────────────────────────────
Open Claude Desktop and try these queries:

  "Search for Ahmedabad talukas"
  "Show me all districts in Gujarat"
  "Get NDVI for Daskroi taluka, Ahmedabad on 2023-08-15"
  "Show NDWI map for Sanand taluka"
  "NDVI timeseries for Daskroi from 2023-01-01 to 2023-12-31 monthly"
  "Compare NDVI of all talukas in Ahmedabad district for 2023-08-15"
  "What dates have imagery for Daskroi between 2023-06-01 and 2023-09-30?"
  "List all available indices"


  TROUBLESHOOTING


ERROR: "Shapefile not found"
  → Check SHAPEFILE_PATH in config.py matches exactly

ERROR: "GEE initialization failed"
  → Make sure Earth Engine API is enabled in GCP
  → Make sure service account is registered in GEE
  → Check JSON key file path in config.py

ERROR: "No cloud-free imagery found"
  → Try a different date (avoid June-September monsoon for India)
  → Increase window_days parameter (e.g. 45 or 60)
  → Best months: November–March for most of India

ERROR: geopandas install fails
  → Use: conda install -c conda-forge geopandas shapely fiona pyproj

ERROR: MCP not showing in Claude Desktop
  → Check claude_desktop_config.json syntax (valid JSON?)
  → Make sure Python is in your system PATH
  → Try: where python   in Command Prompt



  SUPPORTED INDICES (25+)


VEGETATION:  NDVI, EVI, SAVI, MSAVI, GNDVI, NDRE, CIgreen, LAI
WATER:       NDWI, MNDWI, LSWI, AWEInsh, AWEIsh
BUILT-UP:    NDBI, NDBaI, UI, IBI
AGRICULTURE: VCI, NDDI
SOIL:        BSI, SOCI, RI
THERMAL:     LST  (Landsat 8/9 only)


  SATELLITE INFO


Sentinel-2:  10m resolution, 5-day revisit, 2017-present
             Best for: NDVI, NDWI, NDBI, EVI, SAVI, and most indices

Landsat 8/9: 30m resolution, 16-day revisit, 2013-present
             Required for: LST (thermal band)
             Good for: Long historical time series

Cloud masking is AUTOMATIC — no manual filtering needed.
====================================================
