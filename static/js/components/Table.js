
function renderTable(tableName, columns, rows) {
    const host = document.getElementById(tableName);
    host.innerHTML = '';
    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    const thead = document.createElement('thead');
    const thtr = document.createElement('tr');
    columns.forEach((c) => {
      const th = document.createElement('th');
      th.textContent = c;
      th.style.borderBottom = '1px solid #1d222a';
      th.style.textAlign = 'left';
      th.style.padding = '4px 6px';
      thtr.appendChild(th);
    });
    thead.appendChild(thtr);
    table.appendChild(thead);
    const tbody = document.createElement('tbody');
    rows.forEach((r) => {
      const tr = document.createElement('tr');
      columns.forEach((c) => {
        const td = document.createElement('td');
        td.textContent = r[c];
        td.style.padding = '4px 6px';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    host.appendChild(table);
  }

  export default renderTable;