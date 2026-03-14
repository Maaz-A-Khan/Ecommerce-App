// ── Cart State ────────────────────────────────────────────
let cart = JSON.parse(localStorage.getItem('cart')) || [];

// ── Persist to localStorage ───────────────────────────────
function saveCart() {
    localStorage.setItem('cart', JSON.stringify(cart));
}

// ── Attach Event Listeners ────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Products page — wire up Add to Cart buttons
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', () => {
            const code = button.getAttribute('data-code');
            const name = button.getAttribute('data-name');
            const rate = parseFloat(button.getAttribute('data-rate'));
            addToCart(code, name, rate);
        });
    });

    // Sync badge counts on every page load
    updateUI();

    // Checkout page — render items and wire up form submission
    if (document.getElementById('checkout-items')) {
        initCheckout();
    }
});

// ── Cart Logic ────────────────────────────────────────────
function addToCart(code, name, rate) {
    const existingItem = cart.find(item => item.code === code);
    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        cart.push({ code, name, rate, quantity: 1 });
    }
    saveCart();
    updateUI();
}

// ── UI Update ─────────────────────────────────────────────
function updateUI() {
    // Calculate totals
    const totalQty   = cart.reduce((sum, item) => sum + item.quantity, 0);
    const totalPrice = cart.reduce((sum, item) => sum + item.quantity * item.rate, 0);

    // Update cart counts in sidebar and topbar
    const sidebarCount = document.getElementById('sidebar-cart-count');
    const topbarCount  = document.getElementById('topbar-cart-count');
    if (sidebarCount) sidebarCount.textContent = totalQty;
    if (topbarCount)  topbarCount.textContent  = totalQty;

    // Update cart total price (products page summary bar)
    const cartTotal = document.getElementById('cart-total');
    if (cartTotal) cartTotal.textContent = totalPrice.toFixed(2);
}

// ── Checkout Page ─────────────────────────────────────────
function initCheckout() {
    const container = document.getElementById('checkout-items');
    const cartDataInput = document.getElementById('cart-data');
    const form = document.getElementById('checkout-form');

    if (cart.length === 0) {
        // Keep the default "cart is empty" message already in the HTML
        return;
    }

    // Build a summary table of cart items
    const totalPrice = cart.reduce((sum, item) => sum + item.quantity * item.rate, 0);

    const rows = cart.map(item => `
        <tr>
            <td>${item.code}</td>
            <td>${item.name}</td>
            <td>PKR ${item.rate.toFixed(2)}</td>
            <td>${item.quantity}</td>
            <td>PKR ${(item.quantity * item.rate).toFixed(2)}</td>
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
                </tr>
            </thead>
            <tbody>${rows}</tbody>
            <tfoot>
                <tr>
                    <td colspan="4"><strong>Total</strong></td>
                    <td><strong>PKR ${totalPrice.toFixed(2)}</strong></td>
                </tr>
            </tfoot>
        </table>
    `;

    // Populate the hidden input with the cart JSON just before submission
    form.addEventListener('submit', () => {
        cartDataInput.value = JSON.stringify(cart);
    });
}
