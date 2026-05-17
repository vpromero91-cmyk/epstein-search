document.addEventListener('DOMContentLoaded', function(){
  const form = document.getElementById('searchForm');
  const qInput = document.getElementById('q');
  const results = document.getElementById('results');
  const status = document.getElementById('status');
  const pagination = document.getElementById('pagination');
  const imageModal = document.getElementById('imageModal');
  const modalImage = document.getElementById('modalImage');
  const modalInfo = document.getElementById('modalInfo');
  const modalClose = document.querySelector('.modal-close');
  
  let lastQuery = { q: '', search_description: false, search_visible_text: false };
  
  function openImageModal(imageSrc, filepath) {
    modalImage.src = imageSrc;
    
    // Derive PDF path from image filename
    // e.g., EFTA02732405_p0022_large_img001_xref522.png -> EFTA02732405.pdf
    const filename = filepath.split('\\').pop().split('/').pop();
    const baseFileName = filename.split('_')[0];
    const pdfPath = `D:\\Epstein\\${baseFileName}.pdf`;
    
    // Clear and rebuild the file info section
    modalInfo.innerHTML = `
      <div><strong>Image File:</strong></div>
      <div class="modal-filepath">${filepath}</div>
      <button class="copy-btn" data-path="${filepath}">Copy Image Path</button>
      
      <div style="margin-top: 15px;"><strong>Origin PDF:</strong></div>
      <div class="modal-filepath">${pdfPath}</div>
      <button class="copy-btn" data-path="${pdfPath}">Copy PDF Path</button>
    `;
    
    // Attach click handlers to copy buttons
    modalInfo.querySelectorAll('.copy-btn').forEach(btn => {
      btn.onclick = function() {
        const path = this.getAttribute('data-path');
        navigator.clipboard.writeText(path).then(() => {
          const originalText = this.textContent;
          this.textContent = 'Copied!';
          this.classList.add('copied');
          setTimeout(() => {
            this.textContent = originalText;
            this.classList.remove('copied');
          }, 2000);
        }).catch(() => {
          alert('Failed to copy: ' + path);
        });
      };
    });
    
    imageModal.classList.add('show');
  }
  
  function closeImageModal() {
    imageModal.classList.remove('show');
  }
  
  modalClose.onclick = closeImageModal;
  imageModal.onclick = (e) => {
    if (e.target === imageModal) {
      closeImageModal();
    }
  };

  async function doSearch(page = 1) {
    const q = qInput.value.trim();
    const searchDescription = document.getElementById('searchDescription').checked;
    const searchVisibleText = document.getElementById('searchVisibleText').checked;
    
    if (!q) return;
    if (!searchDescription && !searchVisibleText) {
      status.textContent = 'Please select at least one search scope.';
      return;
    }
    
    lastQuery = { q, search_description: searchDescription, search_visible_text: searchVisibleText };
    status.textContent = 'Searching...';
    results.innerHTML = '';
    pagination.innerHTML = '';
    
    try {
      const params = new URLSearchParams({
        q,
        page,
        search_description: searchDescription ? 'true' : 'false',
        search_visible_text: searchVisibleText ? 'true' : 'false',
      });
      const res = await fetch(`/search?${params.toString()}`);
      const data = await res.json();
      const items = data.items || [];
      const total = data.total || 0;
      const totalPages = data.total_pages || 0;
      
      if (!items.length) {
        status.textContent = total === 0 ? 'No results' : 'No results on this page';
        pagination.innerHTML = '';
        return;
      }
      
      status.textContent = `Found ${total} results (page ${page} of ${totalPages})`;
      
      for (const it of items) {
        const card = document.createElement('div');
        card.className = 'card';
        const img = document.createElement('img');
        img.src = `/images/${encodeURIComponent(it.image)}`;
        img.alt = it.description || it.image;
        img.onclick = () => openImageModal(img.src, it.file_name);
        const d = document.createElement('div');
        d.className = 'desc';
        d.textContent = it.description || it.image;
        card.appendChild(img);
        card.appendChild(d);
        if (it.file_name) {
          const f = document.createElement('div');
          f.className = 'fname';
          f.textContent = it.file_name;
          card.appendChild(f);
        }
        if (it.visible_text) {
          const v = document.createElement('div');
          v.className = 'visible-text';
          v.textContent = it.visible_text;
          card.appendChild(v);
        }
        results.appendChild(card);
      }
      
      // render pagination controls
      if (totalPages > 1) {
        const navDiv = document.createElement('div');
        navDiv.style.marginTop = '20px';
        navDiv.style.textAlign = 'center';
        
        const pageWindowSize = 5;
        let startPage = Math.max(1, page - Math.floor(pageWindowSize / 2));
        let endPage = Math.min(totalPages, startPage + pageWindowSize - 1);
        if (endPage - startPage + 1 < pageWindowSize) {
          startPage = Math.max(1, endPage - pageWindowSize + 1);
        }
        
        // First page button
        if (page > 1) {
          const firstBtn = document.createElement('button');
          firstBtn.textContent = '« First';
          firstBtn.onclick = () => doSearch(1);
          firstBtn.style.margin = '0 4px';
          navDiv.appendChild(firstBtn);
        }
        
        // Previous window button
        if (startPage > 1) {
          const prevWinBtn = document.createElement('button');
          prevWinBtn.textContent = '...';
          prevWinBtn.onclick = () => doSearch(startPage - 1);
          prevWinBtn.style.margin = '0 4px';
          navDiv.appendChild(prevWinBtn);
        }
        
        // Page number buttons
        for (let p = startPage; p <= endPage; p++) {
          const pageBtn = document.createElement('button');
          pageBtn.textContent = p;
          pageBtn.style.margin = '0 4px';
          if (p === page) {
            pageBtn.style.fontWeight = 'bold';
            pageBtn.style.backgroundColor = '#ccc';
            pageBtn.disabled = true;
          } else {
            pageBtn.onclick = () => doSearch(p);
          }
          navDiv.appendChild(pageBtn);
        }
        
        // Next window button
        if (endPage < totalPages) {
          const nextWinBtn = document.createElement('button');
          nextWinBtn.textContent = '...';
          nextWinBtn.onclick = () => doSearch(endPage + 1);
          nextWinBtn.style.margin = '0 4px';
          navDiv.appendChild(nextWinBtn);
        }
        
        // Last page button
        if (page < totalPages) {
          const lastBtn = document.createElement('button');
          lastBtn.textContent = 'Last »';
          lastBtn.onclick = () => doSearch(totalPages);
          lastBtn.style.margin = '0 4px';
          navDiv.appendChild(lastBtn);
        }
        
        pagination.appendChild(navDiv);
      }
    } catch (err) {
      console.error(err);
      status.textContent = 'Error searching';
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    doSearch(1);
  });
});
