// ── Cart State (per-user via localStorage) ─────────────────
const storageKey = 'cart_' + (typeof currentUserId !== 'undefined' ? currentUserId : 'guest');
let cart = JSON.parse(localStorage.getItem(storageKey)) || [];

function saveCart() {
    localStorage.setItem(storageKey, JSON.stringify(cart));
}

// ── Quantity Selector (Products page) ─────────────────────
function changeQty(code, delta) {
    const input = document.getElementById('qty-' + code);
    if (!input) return;
    let val = parseInt(input.value) || 1;
    val = Math.max(1, val + delta);
    input.value = val;
}

// ── Attach Event Listeners ────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', () => {
            const code = button.getAttribute('data-code');
            const name = button.getAttribute('data-name');
            const rate = parseFloat(button.getAttribute('data-rate'));
            const qtyInput = document.getElementById('qty-' + code);
            const qty = qtyInput ? Math.max(1, parseInt(qtyInput.value) || 1) : 1;
            addToCart(code, name, rate, qty);
            if (qtyInput) qtyInput.value = 1;
        });
    });

    updateUI();

    if (document.getElementById('checkout-items')) {
        initCheckout();
    }
});

// ── Cart Logic ────────────────────────────────────────────
function addToCart(code, name, rate, qty) {
    const existingItem = cart.find(item => item.code === code);
    if (existingItem) {
        existingItem.quantity += qty;
    } else {
        cart.push({ code, name, rate, quantity: qty });
    }
    saveCart();
    updateUI();
}

function removeFromCart(code) {
    cart = cart.filter(item => item.code !== code);
    saveCart();
    updateUI();
    if (document.getElementById('checkout-items')) {
        initCheckout();
    }
}

// ── UI Update ─────────────────────────────────────────────
function updateUI() {
    const totalQty   = cart.reduce((sum, item) => sum + item.quantity, 0);
    const totalPrice = cart.reduce((sum, item) => sum + item.quantity * item.rate, 0);

    const sidebarCount = document.getElementById('sidebar-cart-count');
    const topbarCount  = document.getElementById('topbar-cart-count');
    if (sidebarCount) sidebarCount.textContent = totalQty;
    if (topbarCount)  topbarCount.textContent  = totalQty;

    const cartTotal = document.getElementById('cart-total');
    if (cartTotal) cartTotal.textContent = totalPrice.toFixed(2);
}

// ── Checkout Page ─────────────────────────────────────────
function initCheckout() {
    const container = document.getElementById('checkout-items');
    const cartDataInput = document.getElementById('cart-data');
    const form = document.getElementById('checkout-form');

    if (cart.length === 0) {
        container.innerHTML = '<p>Your cart is empty. <a href="/products/">Browse products</a>.</p>';
        return;
    }

    const totalPrice = cart.reduce((sum, item) => sum + item.quantity * item.rate, 0);

    const rows = cart.map(item => `
        <tr>
            <td>${item.code}</td>
            <td>${item.name}</td>
            <td>PKR ${item.rate.toFixed(2)}</td>
            <td>${item.quantity}</td>
            <td>PKR ${(item.quantity * item.rate).toFixed(2)}</td>
            <td><button type="button" class="btn-remove-cart" onclick="removeFromCart('${item.code}')">✕ Remove</button></td>
        </tr>
    `).join('');

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Rate</th>
                    <th>Qty</th>
                    <th>Subtotal</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
            <tfoot>
                <tr>
                    <td colspan="4"><strong>Total</strong></td>
                    <td><strong>PKR ${totalPrice.toFixed(2)}</strong></td>
                    <td></td>
                </tr>
            </tfoot>
        </table>
    `;

    form.addEventListener('submit', () => {
        cartDataInput.value = JSON.stringify(cart);
        cart = [];
        saveCart();
    });
}
