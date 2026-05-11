import os
from datetime import datetime, timedelta
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse

app = FastAPI(title="Nasdaq Data Link API Wrapper", version="1.0.0")

# Check for API key at startup
QUANDL_API_KEY = os.environ.get("QUANDL_API_KEY", "")

QUANDL_BASE_URL = "https://data.nasdaq.com/api/v3"


def get_quandl_key() -> str:
    key = QUANDL_API_KEY or os.environ.get("QUANDL_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="QUANDL_API_KEY not configured")
    return key


# Commodity name to dataset code mapping
COMMODITY_MAPPING = {
    "gold": {"code": "LBMA/GOLD", "column": "USD (AM)"},
    "silver": {"code": "LBMA/SILVER", "column": "USD"},
    "oil": {"code": "EIA/PET_RWTC_D", "column": "Value"},
    "wti": {"code": "EIA/PET_RWTC_D", "column": "Value"},
    "brent": {"code": "EIA/PET_RBRTE_D", "column": "Value"},
}

# Macroeconomic indicator mapping
MACRO_MAPPING = {
    "gdp": {"code": "FRED/GDP", "unit": "Billions of Dollars"},
    "unemployment": {"code": "FRED/UNRATE", "unit": "Percent"},
    "cpi": {"code": "FRED/CPIAUCSL", "unit": "Index 1982-1984=100"},
    "inflation": {"code": "FRED/CPIAUCSL", "unit": "Index 1982-1984=100"},
    "fed_funds": {"code": "FRED/DFF", "unit": "Percent"},
    "treasury_10y": {"code": "FRED/DGS10", "unit": "Percent"},
}

HOME_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nasdaq Data Link — Commodities & Economics</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#0D1117;color:#fff;padding:40px 20px;line-height:1.5}
.container{max-width:640px;margin:0 auto;opacity:0;animation:fadeIn .6s ease forwards}
@keyframes fadeIn{to{opacity:1}}
.card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:24px;margin-bottom:20px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.title{font-family:'Courier New',monospace;font-size:28px;color:#F59E0B;font-weight:700}
.health{display:flex;align-items:center;gap:6px;font-size:13px;color:#8B949E}
.health-dot{width:8px;height:8px;background:#0f0;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.subtitle{color:#8B949E;font-size:15px;margin-bottom:24px}
.section-title{font-size:12px;color:#8B949E;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}
.commodity-card{background:rgba(10,10,10,.5);border-radius:12px;padding:16px;border-left:3px solid;position:relative;animation:slideUp .6s ease backwards}
@keyframes slideUp{from{opacity:0;transform:translateY(10px)}}
.commodity-card:nth-child(1){border-left-color:#FFD700;animation-delay:.1s}
.commodity-card:nth-child(2){border-left-color:#C0C0C0;animation-delay:.2s}
.commodity-card:nth-child(3){border-left-color:#3A3A3A;animation-delay:.3s}
.commodity-label{font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:8px}
.commodity-value{font-family:'Courier New',monospace;font-size:32px;color:#fff;font-weight:700;line-height:1}
.commodity-date{font-size:13px;color:#666;margin-top:6px}
.dataset-list{list-style:none}
.dataset-item{padding:12px 0;border-bottom:1px solid rgba(255,255,255,.05);display:flex;justify-content:space-between;align-items:center;font-size:14px}
.dataset-item:last-child{border-bottom:none}
.dataset-code{font-family:'Courier New',monospace;color:#F59E0B;font-weight:600}
.dataset-meta{color:#666;font-size:13px}
.form-group{display:flex;gap:8px;margin-bottom:12px}
input{flex:1;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:12px 16px;color:#fff;font-size:14px;outline:none;transition:.2s}
input:focus{border-color:#F59E0B;background:rgba(255,255,255,.08)}
input::placeholder{color:#666}
button{background:#F59E0B;color:#000;border:none;border-radius:8px;padding:12px 24px;font-size:14px;font-weight:600;cursor:pointer;transition:.2s}
button:hover{background:#D97706;transform:translateY(-1px)}
.try-links{font-size:13px;color:#666}
.try-links a{color:#F59E0B;text-decoration:none;margin:0 2px;cursor:pointer}
.try-links a:hover{text-decoration:underline}
#result{margin-top:16px;padding:16px;background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);border-radius:8px;font-family:'Courier New',monospace;font-size:13px;color:#aaa;white-space:pre-wrap;word-wrap:break-word;display:none}
.loading{color:#F59E0B}
.error{color:#f55}
@media(max-width:640px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="container">
<div class="card">
<div class="header">
<h1 class="title">Nasdaq Data Link</h1>
<div class="health"><span class="health-dot"></span><span id="health-text">checking...</span></div>
</div>
<p class="subtitle">Commodities, futures, and economic data</p>
<div class="section-title">Commodities</div>
<div class="grid" id="commodities">
<div class="commodity-card">
<div class="commodity-label">Gold</div>
<div class="commodity-value loading">--</div>
<div class="commodity-date">Loading...</div>
</div>
<div class="commodity-card">
<div class="commodity-label">Silver</div>
<div class="commodity-value loading">--</div>
<div class="commodity-date">Loading...</div>
</div>
<div class="commodity-card">
<div class="commodity-label">Oil (WTI)</div>
<div class="commodity-value loading">--</div>
<div class="commodity-date">Loading...</div>
</div>
</div>
</div>
<div class="card" style="animation:slideUp .6s .4s ease backwards">
<div class="section-title">Popular Datasets</div>
<ul class="dataset-list">
<li class="dataset-item"><span class="dataset-code">LBMA/GOLD</span><span class="dataset-meta">London gold prices</span></li>
<li class="dataset-item"><span class="dataset-code">LBMA/SILVER</span><span class="dataset-meta">London silver prices</span></li>
<li class="dataset-item"><span class="dataset-code">EIA/PET_RWTC_D</span><span class="dataset-meta">WTI crude oil</span></li>
<li class="dataset-item"><span class="dataset-code">FRED/GDP</span><span class="dataset-meta">US GDP</span></li>
<li class="dataset-item"><span class="dataset-code">FRED/UNRATE</span><span class="dataset-meta">Unemployment rate</span></li>
<li class="dataset-item"><span class="dataset-code">FRED/DGS10</span><span class="dataset-meta">10-year treasury</span></li>
</ul>
</div>
<div class="card" style="animation:slideUp .6s .5s ease backwards">
<form id="searchForm" class="form-group">
<input type="text" id="searchInput" placeholder="gold" required>
<button type="submit">→ search</button>
</form>
<div class="try-links">Try: <a data-query="gold">gold</a> · <a data-query="crude oil">crude oil</a> · <a data-query="inflation">inflation</a> · <a data-query="unemployment">unemployment</a></div>
<div id="result"></div>
</div>
</div>
<script>
const commodities=[
{name:'gold',idx:0},
{name:'silver',idx:1},
{name:'oil',idx:2}
];
function formatPrice(val){
if(val==null)return'--';
return'$'+parseFloat(val).toFixed(2);
}
function escapeHtml(text){
const div=document.createElement('div');
div.textContent=text;
return div.innerHTML;
}
async function fetchHealth(){
const start=Date.now();
try{
const res=await fetch('/health');
const data=await res.json();
const ms=Date.now()-start;
document.getElementById('health-text').textContent='online · '+ms+'ms';
}catch(e){
document.getElementById('health-text').textContent='offline';
document.querySelector('.health-dot').style.background='#f55';
}
}
async function fetchCommodity(comm){
try{
const res=await fetch('/commodity?name='+comm.name);
const data=await res.json();
const card=document.querySelectorAll('.commodity-card')[comm.idx];
const valueEl=card.querySelector('.commodity-value');
const dateEl=card.querySelector('.commodity-date');
if(data.price!=null){
valueEl.textContent=formatPrice(data.price);
valueEl.classList.remove('loading');
const date=new Date(data.date);
const monthNames=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
dateEl.textContent=monthNames[date.getMonth()]+' '+date.getDate()+', '+date.getFullYear();
}else{
valueEl.textContent='--';
valueEl.classList.remove('loading');
dateEl.textContent='No data';
}
}catch(e){
const card=document.querySelectorAll('.commodity-card')[comm.idx];
const valueEl=card.querySelector('.commodity-value');
const dateEl=card.querySelector('.commodity-date');
valueEl.textContent='--';
valueEl.classList.remove('loading');
valueEl.classList.add('error');
dateEl.textContent='Error';
}
}
async function searchDatasets(query){
const resultDiv=document.getElementById('result');
resultDiv.style.display='block';
resultDiv.textContent='Loading...';
resultDiv.className='loading';
try{
const res=await fetch('/search?query='+encodeURIComponent(query));
if(!res.ok){
const err=await res.json();
resultDiv.textContent='Error: '+(err.detail||'Unknown error');
resultDiv.className='error';
return;
}
const data=await res.json();
resultDiv.textContent=JSON.stringify(data,null,2);
resultDiv.className='';
}catch(e){
resultDiv.textContent='Error: '+e.message;
resultDiv.className='error';
}
}
document.getElementById('searchForm').addEventListener('submit',function(e){
e.preventDefault();
const query=document.getElementById('searchInput').value.trim();
if(query)searchDatasets(query);
});
document.querySelectorAll('.try-links a').forEach(link=>{
link.addEventListener('click',function(e){
e.preventDefault();
const query=this.getAttribute('data-query');
document.getElementById('searchInput').value=query;
searchDatasets(query);
});
});
fetchHealth();
commodities.forEach(comm=>fetchCommodity(comm));
</script>
</body>
</html>"""


@app.get("/")
async def root():
    """Rich HTML home page with live Nasdaq Data Link data"""
    return HTMLResponse(content=HOME_HTML)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/commodity")
async def get_commodity(name: str = Query(..., description="Commodity name (gold, silver, oil, wti, brent)")):
    """Get the latest price for a commodity"""
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Normalize the name to lowercase
    normalized_name = name.lower().strip()

    # Check if commodity exists in mapping
    if normalized_name not in COMMODITY_MAPPING:
        available = sorted(COMMODITY_MAPPING.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Commodity '{name}' not found. Available: {', '.join(available)}"
        )

    commodity_info = COMMODITY_MAPPING[normalized_name]
    dataset_code = commodity_info["code"]
    column_name = commodity_info["column"]

    async with httpx.AsyncClient() as client:
        try:
            # Get latest data point
            params = {
                "limit": 1,
                "api_key": get_quandl_key()
            }
            response = await client.get(
                f"{QUANDL_BASE_URL}/datasets/{dataset_code}.json",
                params=params,
                timeout=10.0
            )

            if response.status_code == 400:
                raise HTTPException(status_code=400, detail="Invalid request parameters")
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif response.status_code == 403:
                raise HTTPException(status_code=403, detail="Access forbidden")
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Dataset '{dataset_code}' not found")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            dataset = data.get("dataset", {})
            columns = dataset.get("column_names", [])
            data_rows = dataset.get("data", [])

            if not data_rows:
                raise HTTPException(status_code=404, detail=f"No data available for {name}")

            # Find the column index
            try:
                column_idx = columns.index(column_name)
            except ValueError:
                # If exact column not found, try to find a close match
                column_idx = 1  # Default to second column (first is usually date)

            latest_row = data_rows[0]
            date = latest_row[0]
            price = latest_row[column_idx] if len(latest_row) > column_idx else None

            return {
                "name": normalized_name,
                "price": price,
                "currency": "USD",
                "date": date,
                "dataset": dataset_code,
                "timestamp": timestamp
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise HTTPException(status_code=400, detail="Bad request to Nasdaq Data Link API")
            elif e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            else:
                raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/commodity/history")
async def get_commodity_history(
    name: str = Query(..., description="Commodity name (gold, silver, oil, wti, brent)"),
    days: int = Query(30, description="Number of days of history"),
    collapse: str = Query("daily", description="Frequency: daily, weekly, monthly, quarterly, annual")
):
    """Get historical commodity prices"""
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Normalize the name to lowercase
    normalized_name = name.lower().strip()

    # Check if commodity exists in mapping
    if normalized_name not in COMMODITY_MAPPING:
        available = sorted(COMMODITY_MAPPING.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Commodity '{name}' not found. Available: {', '.join(available)}"
        )

    commodity_info = COMMODITY_MAPPING[normalized_name]
    dataset_code = commodity_info["code"]
    column_name = commodity_info["column"]

    # Calculate start date
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    async with httpx.AsyncClient() as client:
        try:
            # Get historical data
            params = {
                "start_date": start_date,
                "collapse": collapse,
                "api_key": get_quandl_key()
            }
            response = await client.get(
                f"{QUANDL_BASE_URL}/datasets/{dataset_code}.json",
                params=params,
                timeout=10.0
            )

            if response.status_code == 400:
                raise HTTPException(status_code=400, detail="Invalid request parameters")
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            dataset = data.get("dataset", {})
            columns = dataset.get("column_names", [])
            data_rows = dataset.get("data", [])

            # Find the column index
            try:
                column_idx = columns.index(column_name)
            except ValueError:
                column_idx = 1

            # Format historical data
            history = []
            for row in data_rows:
                if len(row) > column_idx:
                    history.append({
                        "date": row[0],
                        "price": row[column_idx]
                    })

            return {
                "name": normalized_name,
                "currency": "USD",
                "data": history,
                "count": len(history),
                "timestamp": timestamp
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise HTTPException(status_code=400, detail="Bad request to Nasdaq Data Link API")
            elif e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            else:
                raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/dataset")
async def get_dataset(
    code: str = Query(..., description="Dataset code (e.g., LBMA/GOLD, FRED/GDP)"),
    limit: int = Query(10, description="Number of data points to return"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    collapse: Optional[str] = Query(None, description="Frequency: daily, weekly, monthly, quarterly, annual")
):
    """Get raw data from any Nasdaq Data Link dataset"""
    timestamp = datetime.utcnow().isoformat() + "Z"

    async with httpx.AsyncClient() as client:
        try:
            # Build params
            params = {
                "limit": limit,
                "api_key": get_quandl_key()
            }
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if collapse:
                params["collapse"] = collapse

            response = await client.get(
                f"{QUANDL_BASE_URL}/datasets/{code}.json",
                params=params,
                timeout=10.0
            )

            if response.status_code == 400:
                raise HTTPException(status_code=400, detail="Invalid request parameters")
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Dataset '{code}' not found")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            dataset = data.get("dataset", {})

            return {
                "code": dataset.get("dataset_code"),
                "name": dataset.get("name"),
                "description": dataset.get("description"),
                "frequency": dataset.get("frequency"),
                "columns": dataset.get("column_names", []),
                "data": dataset.get("data", []),
                "newest_date": dataset.get("newest_available_date"),
                "oldest_date": dataset.get("oldest_available_date"),
                "timestamp": timestamp
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise HTTPException(status_code=400, detail="Bad request to Nasdaq Data Link API")
            elif e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Dataset '{code}' not found")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            else:
                raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/search")
async def search_datasets(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Number of results to return")
):
    """Search for datasets"""
    timestamp = datetime.utcnow().isoformat() + "Z"

    async with httpx.AsyncClient() as client:
        try:
            params = {
                "query": query,
                "per_page": limit,
                "api_key": get_quandl_key()
            }
            response = await client.get(
                f"{QUANDL_BASE_URL}/datasets.json",
                params=params,
                timeout=10.0
            )

            if response.status_code == 400:
                raise HTTPException(status_code=400, detail="Invalid search query")
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            datasets = data.get("datasets", [])

            # Format results
            results = []
            for ds in datasets:
                results.append({
                    "code": ds.get("database_code") + "/" + ds.get("dataset_code"),
                    "name": ds.get("name"),
                    "description": ds.get("description"),
                    "frequency": ds.get("frequency"),
                    "newest_date": ds.get("newest_available_date")
                })

            return {
                "query": query,
                "results": results,
                "count": len(results),
                "timestamp": timestamp
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise HTTPException(status_code=400, detail="Bad request to Nasdaq Data Link API")
            elif e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            else:
                raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/macro")
async def get_macro_indicator(indicator: str = Query(..., description="Indicator name (gdp, unemployment, cpi, inflation, fed_funds, treasury_10y)")):
    """Get a macroeconomic indicator (convenience endpoint using FRED datasets on Quandl)"""
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Normalize the indicator name
    normalized_indicator = indicator.lower().strip()

    # Check if indicator exists in mapping
    if normalized_indicator not in MACRO_MAPPING:
        available = sorted(MACRO_MAPPING.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Indicator '{indicator}' not found. Available: {', '.join(available)}"
        )

    indicator_info = MACRO_MAPPING[normalized_indicator]
    dataset_code = indicator_info["code"]
    unit = indicator_info["unit"]

    async with httpx.AsyncClient() as client:
        try:
            # Get latest data point
            params = {
                "limit": 1,
                "api_key": get_quandl_key()
            }
            response = await client.get(
                f"{QUANDL_BASE_URL}/datasets/{dataset_code}.json",
                params=params,
                timeout=10.0
            )

            if response.status_code == 400:
                raise HTTPException(status_code=400, detail="Invalid request parameters")
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Dataset '{dataset_code}' not found")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            dataset = data.get("dataset", {})
            data_rows = dataset.get("data", [])

            if not data_rows:
                raise HTTPException(status_code=404, detail=f"No data available for {indicator}")

            latest_row = data_rows[0]
            date = latest_row[0]
            value = latest_row[1] if len(latest_row) > 1 else None

            return {
                "indicator": normalized_indicator,
                "value": value,
                "unit": unit,
                "date": date,
                "dataset": dataset_code,
                "timestamp": timestamp
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise HTTPException(status_code=400, detail="Bad request to Nasdaq Data Link API")
            elif e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid API key")
            elif e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Dataset '{dataset_code}' not found")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            else:
                raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Nasdaq Data Link API unavailable")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
