// Cole este script no Console (F12 → Console) na página do tópico do Tibia.
// Itera por TODOS os td.CipPost (cada célula = 1 post) e extrai autor, data e corpo.
(function() {
  const params = new URLSearchParams(window.location.search);
  const threadId = params.get('threadid');
  if (!threadId) {
    alert('Abra uma página de tópico do fórum (URL deve conter threadid=).');
    return;
  }
  const dateRe = /\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}/;

  function parsePage(doc) {
    const posts = [];
    // Cada post está em td.CipPost dentro da tabela de conteúdo do tópico
    const table = doc.querySelector('table.TableContent');
    const root = table || doc;
    const cells = root.querySelectorAll('td.CipPost');
    if (typeof console !== 'undefined' && console.log) console.log('parsePage: células td.CipPost =', cells.length);
    for (let i = 0; i < cells.length; i++) {
      const cell = cells[i];
      const authorEl = cell.querySelector('a[href*="subtopic=characters"][href*="name="]');
      const author = authorEl ? authorEl.textContent.trim() : '';
      const detailsEl = cell.querySelector('.PostDetails');
      const detailsText = detailsEl ? detailsEl.innerText : '';
      const dateMatch = detailsText.match(dateRe);
      const dateStr = dateMatch ? dateMatch[0] : '';
      const bodyEl = cell.querySelector('.PostText');
      let body = bodyEl ? (bodyEl.innerText || bodyEl.textContent || '') : '';
      body = String(body).replace(/\s+/g, ' ').replace(/Edited by [^\n]+ on \d{2}\.\d{2}\.\d{4}[^\n]*/gi, '').trim();
      const postDiv = cell.querySelector('div[id^="Post_"]');
      const post_id = postDiv && postDiv.id ? String(postDiv.id).replace(/^Post_/, '') : null;
      if (author && dateStr) {
        posts.push({ post_id, author, date: dateStr, body });
      }
    }
    return posts;
  }

  function getMaxPage(doc) {
    const links = doc.querySelectorAll('a[href*="pagenumber="]');
    let max = 1;
    for (let i = 0; i < links.length; i++) {
      const href = links[i].getAttribute ? links[i].getAttribute('href') : links[i].href || '';
      const m = String(href).match(/pagenumber=(\d+)/);
      if (m) max = Math.max(max, parseInt(m[1], 10));
    }
    if (max > 1) return max;
    const text = (doc.body && doc.body.innerText) || '';
    const resultsMatch = String(text).match(/Results:\s*(\d+)/i);
    if (resultsMatch) return Math.max(1, Math.ceil(parseInt(resultsMatch[1], 10) / 20));
    return 1;
  }

  const baseUrl = window.location.origin + window.location.pathname + '?' + new URLSearchParams({ action: 'thread', threadid: threadId }).toString();
  const maxPage = getMaxPage(document);

  (async function fetchAll() {
    let allPosts = parsePage(document);
    for (let p = 2; p <= maxPage; p++) {
      const url = baseUrl + (baseUrl.indexOf('?') >= 0 ? '&' : '?') + 'pagenumber=' + p;
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
      // prompt() trunca texto grande; usar textarea na página para copiar o JSON inteiro
      const ta = document.createElement('textarea');
      ta.value = jsonStr;
      ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:fixed;top:20px;left:20px;right:20px;width:calc(100% - 40px);height:calc(100vh - 100px);z-index:99999;padding:12px;font-family:monospace;font-size:12px;background:#1e1e1e;color:#d4d4d4;border:2px solid #0e639c;box-sizing:border-box;';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      alert('O JSON está na caixa que apareceu na tela (' + allPosts.length + ' posts). Use Ctrl+A (selecionar tudo) e Ctrl+C (copiar), depois cole no app. Feche a caixa depois (Delete ou clique fora e apague).');
    }
  })();
})();
