export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // cv.paulharvey.com.au → /cv/ path on main domain
    if (url.hostname === 'cv.paulharvey.com.au') {
      // Serve docs directly if requesting a file
      if (url.pathname.startsWith('/docs/')) {
        url.hostname = 'paulharvey.com.au';
        url.pathname = '/cv' + url.pathname;
        return Response.redirect(url.toString(), 301);
      }
      // Root or any other path → redirect to /cv/
      return Response.redirect('https://paulharvey.com.au/cv/' + url.pathname.replace(/^\/+/, ''), 301);
    }

    // Pass through to static assets for main domain
    return env.ASSETS.fetch(request);
  }
};
