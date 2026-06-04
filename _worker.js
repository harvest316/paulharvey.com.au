export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Decode the path for the "(full)" check, tolerating malformed percent-escapes.
    // A bare decodeURIComponent throws URIError on inputs like "/%" or "/%zz", which
    // would surface as an edge 500 instead of a clean 404; fall back to the raw path.
    let decodedPath;
    try {
      decodedPath = decodeURIComponent(url.pathname);
    } catch {
      decodedPath = url.pathname;
    }

    // Hard block: the real-contact "(full)" resume variants are private (real email +
    // phone) and must never be served publicly. Defence-in-depth in case one is ever
    // mistakenly uploaded to a deployment. no-store so the edge never caches this.
    if (/\(full\)/i.test(decodedPath)) {
      return new Response('Not found', {
        status: 404,
        headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
      });
    }

    // cv.paulharvey.com.au subdomain
    if (url.hostname === 'cv.paulharvey.com.au') {
      // /docs/* → serve docx files from the main domain
      if (url.pathname.startsWith('/docs/')) {
        url.hostname = 'paulharvey.com.au';
        url.pathname = '/cv' + url.pathname;
        return Response.redirect(url.toString(), 301);
      }
      // Anything else → main site root
      return Response.redirect('https://paulharvey.com.au/', 301);
    }

    // Main domain: /cv or /cv/ → /#downloads (page is gone, docs still served at /cv/docs/*)
    if (url.pathname === '/cv' || url.pathname === '/cv/') {
      return Response.redirect('https://paulharvey.com.au/#downloads', 301);
    }

    return env.ASSETS.fetch(request);
  }
};
