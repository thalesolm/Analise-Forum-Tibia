// Cole este script no Console (F12 → Console) na página do tópico do Tibia.
// Ele baixa todas as páginas e copia o JSON para a área de transferência.
(function() {
  const params = new URLSearchParams(window.location.search);
  const threadId = params.get('threadid');
  if (!threadId) {
    alert('Abra uma página de tópico do fórum (URL deve conter threadid=).');
    return;
  }
  const dateRe = /\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}/;
  const postIdRe = /Post\s*#(\d+)/i;

  // Estratégia 1: cada post termina com imagem logo_oldpost ou logo_newpost.
  function parsePageByImages(doc) {
    const posts = [];
    const root = doc.body || doc.documentElement;
    if (!root) return posts;
    const endMarkers = root.querySelectorAll('img[src*="logo_oldpost"], img[src*="logo_newpost"], img[src*="oldpost"], img[src*="newpost"]');
    for (const img of endMarkers) {
      let block = img.parentElement;
      for (let i = 0; i < 30 && block; i++) {
        const text = (block.innerText || '').replace(/\s+/g, ' ');
        const dateMatch = text.match(dateRe);
        const authorLink = block.querySelector('a[href*="subtopic=characters"][href*="name="]');
        if (dateMatch && authorLink) {
          const author = (authorLink.textContent || '').trim();
          if (!author || author.length > 50) {
            block = block.parentElement;
            continue;
          }
          const dateStr = dateMatch[0];
          let body = text.replace(dateStr, '').replace(/Edited by [^\n]+ on \d{2}\.\d{2}\.\d{4}[^\n]*/gi, '').replace(/_+/g, '').replace(/\s+/g, ' ').trim();
          const postIdMatch = text.match(postIdRe);
          posts.push({ post_id: postIdMatch ? postIdMatch[1] : null, author, date: dateStr, body });
          break;
        }
        block = block.parentElement;
      }
    }
    return posts;
  }

  // Estratégia 2 (fallback): links de autor; menor ancestral com 1 data.
  const SKIP = /^(community|tibia|forum|board jump|thread jump|post jump|page jump|choose board|section)$/i;
  function parsePageByLinks(doc) {
    const posts = [];
    const seen = new Set();
    const root = doc.body || doc.documentElement;
    if (!root) return posts;
    const links = root.querySelectorAll('a[href*="subtopic=characters"][href*="name="]');
    for (const a of links) {
      const author = (a.textContent || '').trim();
      if (!author || author.length > 50 || SKIP.test(author)) continue;
      let el = a.parentElement;
      let best = null, bestEl = null, bestLen = Infinity;
      for (let i = 0; i < 25 && el; i++) {
        const text = (el.innerText || '').replace(/\s+/g, ' ');
        const dates = text.match(/\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}/g);
        if (dates && dates.length === 1 && text.indexOf(author) !== -1 && text.length > 50 && text.length < bestLen) {
          bestLen = text.length;
          best = text;
          bestEl = el;
        }
        el = el.parentElement;
      }
      if (!best || !bestEl) continue;
      const firstInBlock = bestEl.querySelector('a[href*="subtopic=characters"][href*="name="]');
      if (firstInBlock !== a) continue;
      const dateStr = best.match(/\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}/)[0];
      const key = author + '|' + dateStr;
      if (seen.has(key)) continue;
      seen.add(key);
      let body = best.replace(dateStr, '').replace(/Edited by [^\n]+ on \d{2}\.\d{2}\.\d{4}[^\n]*/gi, '').replace(/_+/g, '').replace(/\s+/g, ' ').trim();
      const postIdMatch = best.match(postIdRe);
      posts.push({ post_id: postIdMatch ? postIdMatch[1] : null, author, date: dateStr, body });
    }
    return posts;
  }

  function parsePage(doc) {
    let posts = parsePageByImages(doc);
    if (posts.length <= 1) {
      const byLinks = parsePageByLinks(doc);
      if (byLinks.length > posts.length) posts = byLinks;
    }
    return posts;
  }

  function getMaxPage(doc) {
    const pageLinks = Array.from((doc.body && doc.body.querySelectorAll('a[href*="pagenumber="]')) || doc.querySelectorAll('a[href*="pagenumber="]') || []);
    const pageNumbers = pageLinks.map(a => {
      const href = a.getAttribute('href') || a.href || '';
      const m = href.match(/pagenumber=(\d+)/);
      return m ? parseInt(m[1], 10) : null;
    }).filter(Boolean);
    if (pageNumbers.length > 0) return Math.max(...pageNumbers);
    const bodyText = (doc.body && doc.body.innerText) || (doc.documentElement && doc.documentElement.innerText) || '';
    const resultsMatch = bodyText.match(/Results:\s*(\d+)/i);
    if (resultsMatch) return Math.max(1, Math.ceil(parseInt(resultsMatch[1], 10) / 20));
    return 1;
  }

  const baseUrl = window.location.origin + window.location.pathname + '?' + new URLSearchParams({ action: 'thread', threadid: threadId }).toString();
  const maxPage = getMaxPage(document);

  (async function fetchAll() {
    let allPosts = parsePage(document);
    for (let p = 2; p <= maxPage; p++) {
      const url = baseUrl + (baseUrl.includes('?') ? '&' : '?') + 'pagenumber=' + p;
      try {
        const resp = await fetch(url);
        const html = await resp.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const pagePosts = parsePage(doc);
        allPosts = allPosts.concat(pagePosts);
      } catch (e) {
        console.warn('Erro na página ' + p, e);
      }
    }
    const data = { thread_id: threadId, title: null, posts: allPosts };
    const jsonStr = JSON.stringify(data);
    try {
      await navigator.clipboard.writeText(jsonStr);
      alert('JSON copiado! (' + allPosts.length + ' posts de ' + maxPage + ' página(s)). Cole no app e clique em "Carregar e analisar".');
    } catch (e) {
      prompt('Copie o JSON abaixo (Ctrl+C):', jsonStr);
    }
  })();
})();
