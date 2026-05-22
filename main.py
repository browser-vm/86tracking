import urllib.parse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import modal

# 1. Define the Modal App and the environment (Image)
app = modal.App("url-cleaner-api")
image = modal.Image.debian_slim().pip_install("fastapi", "pydantic")

# 2. Initialize FastAPI
web_app = FastAPI(
    title="86Tracking URL Tracking Remover",
    description="An API that strips analytics and tracking parameters from URLs."
)

# 3. Define the list of common tracking parameters to remove
# This covers Google Analytics, Facebook, Instagram, Mailchimp, Microsoft, etc.
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
    # Parse the URL into components
    parsed = urllib.parse.urlparse(url)
    
    # Extract query parameters as a list of (key, value) tuples
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    
    # Filter out any parameter that exists in our tracking list
    cleaned_params = [
        (k, v) for k, v in query_params 
        if k.lower() not in TRACKING_PARAMS
    ]
    
    # Re-encode the query string
    new_query = urllib.parse.urlencode(cleaned_params)
    
    # Reconstruct the URL with the cleaned query string
    cleaned_url = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    return cleaned_url

# 6. Define the FastAPI endpoint
@web_app.post("/clean", response_model=URLResponse)
def clean_tracking_link(request: URLRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
    
    # Add a fallback scheme if the user passed a URL without http:// or https://
    target_url = request.url
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    cleaned = strip_tracking_params(target_url)
    
    return URLResponse(
        original_url=request.url,
        cleaned_url=cleaned
    )

# 7. Mount the FastAPI app to Modal using the ASGI decorator
@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    return web_app