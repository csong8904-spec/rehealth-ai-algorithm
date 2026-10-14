# ReHealth AI research site

This directory is a standalone, buildless static site for `ai.jsruihe.cn`. It serves a fixed synthetic report example and links to the public research repository. It has no health data input, API call, analytics script, or browser storage.

## Build assets and preview

From the repository root:

```bash
python scripts/build_site_assets.py
cd site
python -m http.server 8000
```

Open `http://127.0.0.1:8000/`. The site can be deployed by copying the contents of `site/` to a static web root. Do not use the repository root as the web root.

## Example Nginx virtual host

The file `nginx-ai.jsruihe.cn.conf.example` is a template, not a command to overwrite the current Nginx configuration. Confirm the server's existing site files and certificate method before applying it. Replace the `root` path with the actual site directory; run `nginx -t` before reload. Issue a certificate for `ai.jsruihe.cn`, then configure a 443 server block and HTTP to HTTPS redirect using the certificate tool's output. Keep the current `jsruihe.cn` and `www.jsruihe.cn` server blocks intact.

Deployment verification:

```bash
dig +short ai.jsruihe.cn A
curl -I http://ai.jsruihe.cn/
curl -I https://ai.jsruihe.cn/
curl -I https://ai.jsruihe.cn/privacy.html
```

Before public launch, replace the draft privacy notice with the operator's reviewed version and add applicable ICP and algorithm filing disclosures after the corresponding numbers are issued. The current PPG research candidate is blocked from live health conclusions.
