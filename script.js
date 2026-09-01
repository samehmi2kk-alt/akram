function submitLogin() {
    const user = document.getElementById('admin-user').value;
    const pass = document.getElementById('admin-pass').value;
    fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `username=${encodeURIComponent(user)}&password=${encodeURIComponent(pass)}`
    })
    .then(res => res.json())
    .then(data => {
        if(data.success) {
            location.reload();
        } else {
            alert(data.message);
        }
    });
}

function filterCategory(catId) {
    const items = document.querySelectorAll('.product-card-item');
    items.forEach(item => {
        if(catId === 'all' || item.getAttribute('data-cat') === catId) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function toggleSelectAll(source) {
    const checkboxes = document.querySelectorAll('.inv-checkbox');
    checkboxes.forEach(cb => cb.checked = source.checked);
}

function printSingleInvoice(id) {
    window.print();
}

function printSelectedInvoices() {
    window.print();
}

function searchFunction() {
    let input = document.getElementById("search-input").value.toLowerCase();
    let rows = document.querySelectorAll("tbody tr");
    rows.forEach(row => {
        let text = row.innerText.toLowerCase();
        row.style.display = text.includes(input) ? "" : "none";
    });
}