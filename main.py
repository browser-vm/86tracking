import urllib.parse
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import modal

# 1. Define the Modal App and the environment (Image)
app = modal.App("url-cleaner-api")
image = modal.Image.debian_slim().pip_install("fastapi", "pydantic")

# 2. Initialize FastAPI
web_app = FastAPI(
    title="URL Tracking Remover",
    description="An API that strips analytics and tracking parameters from URLs."
)

# 3. Define the list of common tracking parameters to remove
TRACKING_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', 'mc_cid', 'mc_eid', '_ga', 'igshid',
        'ref', 'ref_src', 'ref_url', 'icid', 'mkt_tok', 'wickedid', 'yclid',
        'oly_enc_id', 'oly_anon_id'
}

# 4. Define Pydantic models for request and response validation
class URLRequest(BaseModel):
    url: str

class URLResponse(BaseModel):
    original_url: str
    cleaned_url: str

# 5. Core logic to clean the URL
def strip_tracking_params(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    
    cleaned_params = [
        (k, v) for k, v in query_params 
        if k.lower() not in TRACKING_PARAMS
    ]
    
    new_query = urllib.parse.urlencode(cleaned_params)
    
    cleaned_url = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    return cleaned_url

# 6. Redirect the root URL to the interactive /docs page
@web_app.get("/", include_in_schema=False)
def docs_redirect():
    """Redirects the base URL to the Swagger UI."""
    return RedirectResponse(url="/docs")

# 7. Define the FastAPI endpoint
@web_app.post("/clean", response_model=URLResponse)
def clean_tracking_link(request: URLRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
    
    target_url = request.url
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    cleaned = strip_tracking_params(target_url)
    
    return URLResponse(
        original_url=request.url,
        cleaned_url=cleaned
    )

# 8. Mount the FastAPI app to Modal using the ASGI decorator
@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    return web_app