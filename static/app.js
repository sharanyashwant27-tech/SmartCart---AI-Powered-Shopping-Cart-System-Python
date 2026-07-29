/**
 * SmartCart storefront — served on http://localhost:8904
 */
const API = "/api/v1";

function readUser() {
  try {
    return JSON.parse(localStorage.getItem("sc_user") || "null");
  } catch {
    localStorage.removeItem("sc_user");
    return null;
  }
}

const state = {
  page: "shop",
  token: localStorage.getItem("sc_token") || "",
  refresh: localStorage.getItem("sc_refresh") || "",
  user: readUser(),
  products: [],
  categories: [],
  cart: null,
  cartCount: Number(localStorage.getItem("sc_cart_count") || 0),
  couponCode: localStorage.getItem("sc_coupon") || "",
  pendingPayment: null,
  lastOrder: null,
  dash: null,
  productId: null,
};

function setCoupon(code) {
  state.couponCode = code || "";
  if (state.couponCode) localStorage.setItem("sc_coupon", state.couponCode);
  else localStorage.removeItem("sc_coupon");
}

function setCartCount(n) {
  state.cartCount = Number(n) || 0;
  localStorage.setItem("sc_cart_count", String(state.cartCount));
  const badge = document.getElementById("cart-badge");
  if (badge) {
    badge.textContent = state.cartCount > 0 ? String(state.cartCount) : "";
    badge.classList.toggle("hidden", state.cartCount <= 0);
  }
}

async function refreshCartSummary() {
  if (!state.token) {
    setCartCount(0);
    return null;
  }
  try {
    const cart = await api("GET", "/cart");
    state.cart = cart;
    setCartCount(cart.item_count || (cart.items || []).length || 0);
    return cart;
  } catch {
    return null;
  }
}

function money(v) {
  const n = Number(v || 0);
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

async function downloadBill(orderId, orderNumber) {
  if (!state.token) {
    toast("Sign in to download bill", "error");
    return;
  }
  try {
    const url = `${API}/orders/${orderId}/invoice`;
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t || "Could not download bill");
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `bill-${orderNumber || orderId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
    toast("Bill downloaded");
  } catch (e) {
    toast(e.message, "error");
  }
}

const PAY_METHODS = [
  { id: "card", label: "Card", hint: "Debit / credit card" },
  { id: "upi", label: "UPI", hint: "GPay, PhonePe, BHIM" },
  { id: "netbanking", label: "Net Banking", hint: "Internet banking" },
  { id: "wallet", label: "Wallet", hint: "Paytm / Amazon Pay" },
  { id: "cod", label: "Cash on Delivery", hint: "Pay when delivered" },
];


function toast(msg, type = "ok") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = `toast show ${type}`;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove("show"), 2800);
}

function saveAuth(data) {
  state.token = data.access_token;
  state.refresh = data.refresh_token || "";
  state.user = data.user;
  localStorage.setItem("sc_token", state.token);
  localStorage.setItem("sc_refresh", state.refresh);
  localStorage.setItem("sc_user", JSON.stringify(state.user));
  renderChrome();
}

function clearAuth() {
  state.token = "";
  state.refresh = "";
  state.user = null;
  state.cart = null;
  state.pendingPayment = null;
  localStorage.removeItem("sc_token");
  localStorage.removeItem("sc_refresh");
  localStorage.removeItem("sc_user");
  setCartCount(0);
  renderChrome();
}

function isAdmin() {
  return state.user && (state.user.role === "admin" || state.user.role === "Admin");
}

async function api(method, path, body, params) {
  const url = new URL(API + path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = { detail: text }; }
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    if (data) {
      const errs = data.error?.extra?.errors;
      if (Array.isArray(errs) && errs.length) {
        detail = errs.map((d) => d.msg || JSON.stringify(d)).join("; ");
      } else if (data.error && data.error.detail) {
        detail = data.error.detail;
      } else if (typeof data.detail === "string") {
        detail = data.detail;
      } else if (Array.isArray(data.detail)) {
        detail = data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
      } else if (data.message) {
        detail = data.message;
      }
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function renderChrome() {
  const box = document.getElementById("user-box");
  const navAccount = document.getElementById("nav-account");
  if (navAccount) {
    navAccount.textContent = state.user ? "My Account" : "Login";
  }
  if (state.user) {
    const name = state.user.name || state.user.full_name || "User";
    const role = (state.user.role || "customer").toLowerCase();
    box.innerHTML = `
      <div><strong>${escapeHtml(name)}</strong></div>
      <div class="email">${escapeHtml(state.user.email || "")}</div>
      <span class="role-pill ${role === "admin" ? "admin" : "customer"}">${escapeHtml(role)}</span>
      <button class="nav-btn" style="margin-top:0.6rem" id="btn-logout">Logout</button>
    `;
    document.getElementById("btn-logout").onclick = () => {
      clearAuth();
      toast("Logged out");
      navigate("account");
    };
  } else {
    box.innerHTML = `
      <div class="email">Browsing as guest</div>
      <button class="nav-btn" style="margin-top:0.6rem" id="btn-goto-login">Login / Register</button>
    `;
    document.getElementById("btn-goto-login").onclick = () => navigate("account");
  }
  document.getElementById("nav-admin").classList.toggle("hidden", !isAdmin());
  const navCatalog = document.getElementById("nav-catalog");
  if (navCatalog) navCatalog.classList.toggle("hidden", !isAdmin());
  document.querySelectorAll(".nav-btn[data-page]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === state.page);
  });
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function navigate(page, extra) {
  state.page = page;
  if (extra && extra.productId) state.productId = extra.productId;
  renderChrome();
  const views = {
    shop: viewShop,
    product: viewProduct,
    cart: viewCart,
    checkout: viewCheckout,
    payment: viewPayment,
    confirmation: viewConfirmation,
    orders: viewOrders,
    account: viewAccount,
    admin: viewAdmin,
    catalog: viewCatalog,
  };
  (views[page] || viewShop)();
}

async function viewShop() {
  const root = document.getElementById("app");
  root.innerHTML = `
    <div class="hero">
      <h1 class="brand-title" id="hero-home" title="Go to shop" role="link" tabindex="0">SmartCart</h1>
      <p>Curated products · Fast checkout · Transparent totals</p>
      <div class="links-row">
        <a href="/docs">API Docs</a>
        <a href="/health">Health</a>
      </div>
    </div>
    <div class="toolbar">
      <label>Search<input id="q" placeholder="Headphones, jacket…" /></label>
      <label>Category
        <select id="cat"><option value="">All</option></select>
      </label>
      <label>&nbsp;<button class="btn btn-primary" id="btn-search">Search</button></label>
    </div>
    <div id="product-grid" class="grid"><div class="muted">Loading…</div></div>
  `;

  try {
    state.categories = await api("GET", "/categories", null, { active_only: true });
    const cat = document.getElementById("cat");
    state.categories.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      cat.appendChild(opt);
    });
  } catch (e) {
    toast(e.message, "error");
  }

  const heroHome = document.getElementById("hero-home");
  if (heroHome) {
    const goShop = () => navigate("shop");
    heroHome.addEventListener("click", goShop);
    heroHome.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        goShop();
      }
    });
  }

  async function load() {
    const q = document.getElementById("q").value.trim();
    const category_id = document.getElementById("cat").value;
    try {
      const data = await api("GET", "/products", null, {
        page: 1,
        page_size: 24,
        active_only: true,
        q: q || undefined,
        category_id: category_id || undefined,
      });
      state.products = data.items || [];
      const grid = document.getElementById("product-grid");
      if (!state.products.length) {
        grid.innerHTML = `<div class="muted">No products found.</div>`;
        return;
      }
      grid.innerHTML = state.products
        .map(
          (p) => `
        <article class="card">
          ${p.image_url || p.image ? `<img src="${escapeHtml(p.image_url || p.image)}" alt="" />` : ""}
          ${p.is_featured ? `<span class="badge">Featured</span>` : ""}
          <h3>${escapeHtml(p.name)}</h3>
          <div class="muted">${escapeHtml((p.category && p.category.name) || "General")}</div>
          <div class="price">${money(p.price)}</div>
          <div class="muted">Stock: ${p.stock_quantity ?? p.stock ?? 0}</div>
          <div class="btn-row">
            <button class="btn btn-ghost" data-view="${p.id}">Details</button>
            <button class="btn btn-primary" data-add="${p.id}">Add</button>
          </div>
        </article>`
        )
        .join("");
      grid.querySelectorAll("[data-view]").forEach((b) =>
        b.addEventListener("click", () => navigate("product", { productId: Number(b.dataset.view) }))
      );
      grid.querySelectorAll("[data-add]").forEach((b) =>
        b.addEventListener("click", () => addToCart(Number(b.dataset.add)))
      );
    } catch (e) {
      toast(e.message, "error");
    }
  }

  document.getElementById("btn-search").onclick = load;
  document.getElementById("q").addEventListener("keydown", (e) => {
    if (e.key === "Enter") load();
  });
  await load();
}

async function viewProduct() {
  const root = document.getElementById("app");
  root.innerHTML = `<div class="muted">Loading product…</div>`;
  try {
    const p = await api("GET", `/products/${state.productId}`);
    root.innerHTML = `
      <button class="btn btn-ghost" id="back">← Back to shop</button>
      <div class="panel" style="margin-top:1rem;display:grid;grid-template-columns:1fr 1fr;gap:1.25rem">
        <div>
          ${p.image_url || p.image ? `<img src="${escapeHtml(p.image_url || p.image)}" style="width:100%;border-radius:14px" alt="" />` : ""}
        </div>
        <div>
          <h2 style="font-family:Sora,sans-serif;font-size:1.8rem;letter-spacing:-0.03em">${escapeHtml(p.name)}</h2>
          <div class="price" style="margin:0.5rem 0">${money(p.price)}</div>
          <p class="muted" style="margin-bottom:1rem">${escapeHtml(p.description || "No description.")}</p>
          <div class="field">
            <label>Quantity</label>
            <input type="number" id="qty" min="1" max="50" value="1" />
          </div>
          <div class="btn-row">
            <button class="btn btn-primary" id="add">Add to Cart</button>
            <button class="btn btn-ghost" id="wish">Wishlist</button>
          </div>
        </div>
      </div>`;
    document.getElementById("back").onclick = () => navigate("shop");
    document.getElementById("add").onclick = () =>
      addToCart(p.id, Number(document.getElementById("qty").value || 1));
    document.getElementById("wish").onclick = async () => {
      if (!state.token) return toast("Sign in required", "error");
      try {
        await api("POST", "/wishlist", { product_id: p.id });
        toast("Added to wishlist");
      } catch (e) {
        toast(e.message, "error");
      }
    };
  } catch (e) {
    toast(e.message, "error");
    navigate("shop");
  }
}

async function addToCart(productId, quantity = 1) {
  if (!state.token) {
    toast("Please sign in to add items", "error");
    navigate("account");
    return;
  }
  try {
    await api("POST", "/cart/items", { product_id: productId, quantity });
    await refreshCartSummary();
    toast("Added to cart");
  } catch (e) {
    toast(e.message, "error");
  }
}

async function viewCart() {
  const root = document.getElementById("app");
  if (!state.token) {
    root.innerHTML = `<div class="panel"><p>Please <a href="#" id="go-account" style="color:var(--teal-deep);font-weight:700">sign in</a> to view your cart.</p></div>`;
    document.getElementById("go-account").onclick = (e) => {
      e.preventDefault();
      navigate("account");
    };
    return;
  }
  root.innerHTML = `
    <div class="hero">
      <h1>Your Cart</h1>
      <p>Update quantities, apply coupons, then checkout</p>
    </div>
    <div id="cart-body" class="panel">Loading…</div>`;
  try {
    const cart = await api("GET", "/cart");
    state.cart = cart;
    setCartCount(cart.item_count || (cart.items || []).length || 0);
    const body = document.getElementById("cart-body");
    const items = cart.items || [];
    if (!items.length) {
      body.innerHTML = `
        <p class="muted">Cart is empty.</p>
        <button class="btn btn-primary" id="shop">Continue shopping</button>`;
      document.getElementById("shop").onclick = () => navigate("shop");
      return;
    }
    const couponVal = escapeHtml(state.couponCode || cart.coupon_code || "");
    body.innerHTML = `
      ${items
        .map(
          (it) => `
        <div class="cart-item">
          <img src="${escapeHtml(it.product?.image_url || it.product?.image || "")}" alt="" />
          <div>
            <strong>${escapeHtml(it.product?.name || "Item")}</strong>
            <div class="muted">${money(it.product?.price)} each</div>
            <div class="qty-row">
              <button class="btn btn-ghost qty-btn" data-dec="${it.id}">−</button>
              <span class="qty-val">${it.quantity}</span>
              <button class="btn btn-ghost qty-btn" data-inc="${it.id}" data-q="${it.quantity}">+</button>
            </div>
          </div>
          <div style="text-align:right">
            <div class="price">${money(it.line_total)}</div>
            <button class="btn btn-danger" data-rm="${it.id}" style="margin-top:0.35rem">Remove</button>
          </div>
        </div>`
        )
        .join("")}
      <div class="totals">
        <div class="row"><span>Subtotal</span><span>${money(cart.subtotal)}</span></div>
        <div class="row"><span>Discount</span><span>-${money(cart.discount_amount)}</span></div>
        <div class="row"><span>Shipping</span><span>${money(cart.shipping_amount)}</span></div>
        <div class="row"><span>Tax</span><span>${money(cart.tax_amount)}</span></div>
        <div class="row grand"><span>Total</span><span>${money(cart.total)}</span></div>
      </div>
      <div class="field" style="margin-top:1rem">
        <label>Coupon code</label>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap">
          <input id="coupon" placeholder="WELCOME10 or SAVE5" value="${couponVal}" style="flex:1" />
          <button class="btn btn-ghost" id="apply-coupon">Apply</button>
        </div>
        <p class="muted" style="margin-top:0.35rem">Try <code>WELCOME10</code> (10%) or <code>SAVE5</code> ($5 off)</p>
      </div>
      <button class="btn btn-primary btn-block" id="to-checkout" style="margin-top:0.75rem">Proceed to checkout</button>
    `;

    body.querySelectorAll("[data-rm]").forEach((b) =>
      b.addEventListener("click", async () => {
        try {
          await api("DELETE", `/cart/items/${b.dataset.rm}`);
          toast("Removed");
          viewCart();
        } catch (e) {
          toast(e.message, "error");
        }
      })
    );
    body.querySelectorAll("[data-inc]").forEach((b) =>
      b.addEventListener("click", async () => {
        const q = Number(b.dataset.q || 1) + 1;
        try {
          await api("PATCH", `/cart/items/${b.dataset.inc}`, { quantity: q });
          viewCart();
        } catch (e) {
          toast(e.message, "error");
        }
      })
    );
    body.querySelectorAll("[data-dec]").forEach((b) =>
      b.addEventListener("click", async () => {
        const item = items.find((i) => String(i.id) === String(b.dataset.dec));
        const q = Math.max(1, (item?.quantity || 1) - 1);
        try {
          if (q === 1 && item?.quantity === 1) {
            /* keep at 1 */
          }
          await api("PATCH", `/cart/items/${b.dataset.dec}`, { quantity: q });
          viewCart();
        } catch (e) {
          toast(e.message, "error");
        }
      })
    );
    document.getElementById("apply-coupon").onclick = async () => {
      const code = document.getElementById("coupon").value.trim();
      if (!code) {
        toast("Enter a coupon code", "error");
        return;
      }
      try {
        const updated = await api("POST", "/cart/apply-coupon", { code });
        setCoupon(code);
        state.cart = updated;
        toast(`Coupon ${code} applied · −${money(updated.discount_amount)}`);
        viewCart();
      } catch (e) {
        toast(e.message, "error");
      }
    };
    document.getElementById("to-checkout").onclick = () => navigate("checkout");
  } catch (e) {
    toast(e.message, "error");
  }
}

async function viewCheckout() {
  const root = document.getElementById("app");
  if (!state.token) {
    navigate("account");
    return;
  }

  let cart = state.cart;
  try {
    cart = await api("GET", "/cart");
    state.cart = cart;
    setCartCount(cart.item_count || 0);
  } catch (e) {
    toast(e.message, "error");
    return;
  }

  if (!cart?.items?.length) {
    root.innerHTML = `
      <div class="hero"><h1>Checkout</h1><p>Your cart is empty</p></div>
      <div class="panel"><button class="btn btn-primary" id="shop">Go shopping</button></div>`;
    document.getElementById("shop").onclick = () => navigate("shop");
    return;
  }

  const user = state.user || {};
  const defaultAddr = [
    user.address_line1,
    user.address_line2,
    [user.city, user.state, user.postal_code].filter(Boolean).join(", "),
    user.country,
  ]
    .filter(Boolean)
    .join(", ");

  root.innerHTML = `
    <div class="hero">
      <h1>Checkout</h1>
      <p>Choose payment method · then pay & download bill</p>
    </div>
    <div class="checkout-grid">
      <div class="panel">
        <h2>Shipping</h2>
        <div class="field">
          <label>Shipping address</label>
          <textarea id="ship" placeholder="123 Main St, City, State, ZIP, Country">${escapeHtml(defaultAddr)}</textarea>
        </div>
        <div class="field">
          <label>Billing address (optional)</label>
          <textarea id="bill" placeholder="Same as shipping if blank"></textarea>
        </div>
        <div class="field">
          <label>Coupon code</label>
          <input id="c_code" placeholder="WELCOME10" value="${escapeHtml(state.couponCode || "")}" />
        </div>
        <div class="field">
          <label>Order notes</label>
          <input id="notes" placeholder="Leave at door…" />
        </div>

        <h2 style="margin-top:1rem">Payment method</h2>
        <div class="pay-methods" id="pay-methods">
          ${PAY_METHODS.map(
            (m, i) => `
            <label class="pay-method ${i === 0 ? "active" : ""}">
              <input type="radio" name="pay_method" value="${m.id}" ${i === 0 ? "checked" : ""} />
              <span><strong>${m.label}</strong><br/><small>${m.hint}</small></span>
            </label>`
          ).join("")}
        </div>
        <div id="method-fields"></div>

        <div class="auth-error" id="checkout-error"></div>
        <button class="btn btn-primary btn-block" id="place">Continue to payment</button>
        <button class="btn btn-ghost btn-block" id="back-cart" style="margin-top:0.5rem">Back to cart</button>
      </div>
      <div class="panel">
        <h2>Order summary</h2>
        ${(cart.items || [])
          .map(
            (it) => `
          <div class="summary-line">
            <span>${escapeHtml(it.product?.name || "Item")} × ${it.quantity}</span>
            <span>${money(it.line_total)}</span>
          </div>`
          )
          .join("")}
        <div class="totals" style="margin-top:0.75rem">
          <div class="row"><span>Subtotal</span><span>${money(cart.subtotal)}</span></div>
          <div class="row"><span>Discount</span><span>-${money(cart.discount_amount)}</span></div>
          <div class="row"><span>Shipping</span><span>${money(cart.shipping_amount)}</span></div>
          <div class="row"><span>Tax</span><span>${money(cart.tax_amount)}</span></div>
          <div class="row grand"><span>Total due</span><span>${money(cart.total)}</span></div>
        </div>
      </div>
    </div>`;

  function renderMethodFields() {
    const method = document.querySelector('input[name="pay_method"]:checked')?.value || "card";
    const box = document.getElementById("method-fields");
    document.querySelectorAll(".pay-method").forEach((el) => {
      el.classList.toggle("active", el.querySelector("input")?.value === method);
    });
    if (method === "upi") {
      box.innerHTML = `<div class="field"><label>UPI ID / VPA</label><input id="upi_id" placeholder="name@upi" value="shopper@oksbi" /></div>`;
    } else if (method === "netbanking") {
      box.innerHTML = `<div class="field"><label>Bank</label>
        <select id="bank">
          <option>HDFC Bank</option><option>ICICI Bank</option><option>SBI</option>
          <option>Axis Bank</option><option>Kotak Mahindra</option><option>Demo Bank</option>
        </select></div>`;
    } else if (method === "wallet") {
      box.innerHTML = `<div class="field"><label>Wallet</label>
        <select id="wallet">
          <option>PhonePe</option><option>Google Pay</option><option>Paytm</option><option>Amazon Pay</option>
        </select></div>`;
    } else if (method === "cod") {
      box.innerHTML = `<p class="muted">Pay cash to the delivery partner. A bill is still generated for your records.</p>`;
    } else {
      box.innerHTML = `<p class="muted">Card details are collected securely on the next step.</p>`;
    }
  }

  document.querySelectorAll('input[name="pay_method"]').forEach((r) => {
    r.addEventListener("change", renderMethodFields);
  });
  renderMethodFields();

  document.getElementById("back-cart").onclick = () => navigate("cart");
  document.getElementById("place").onclick = async () => {
    const err = document.getElementById("checkout-error");
    err.textContent = "";
    const shipping_address = document.getElementById("ship").value.trim();
    const billing_address = document.getElementById("bill").value.trim();
    if (shipping_address.length < 10) {
      err.textContent = "Enter a full shipping address (at least 10 characters).";
      return;
    }
    const payment_method = document.querySelector('input[name="pay_method"]:checked')?.value || "card";
    const payment_details = {};
    if (payment_method === "upi") payment_details.upi_id = document.getElementById("upi_id")?.value.trim();
    if (payment_method === "netbanking") payment_details.bank = document.getElementById("bank")?.value;
    if (payment_method === "wallet") payment_details.wallet = document.getElementById("wallet")?.value;

    const btn = document.getElementById("place");
    btn.disabled = true;
    btn.textContent = "Creating order…";
    try {
      const coupon = document.getElementById("c_code").value.trim();
      if (coupon) setCoupon(coupon);
      const result = await api("POST", "/checkout", {
        shipping_address,
        billing_address: billing_address || null,
        coupon_code: coupon || null,
        notes: document.getElementById("notes").value.trim() || null,
        payment_method,
        payment_details,
      });
      state.pendingPayment = result;
      setCartCount(0);
      toast(result.message || "Order created — complete payment");
      navigate("payment");
    } catch (e) {
      err.textContent = e.message;
      toast(e.message, "error");
      btn.disabled = false;
      btn.textContent = "Continue to payment";
    }
  };
}

async function viewPayment() {
  const root = document.getElementById("app");
  const pending = state.pendingPayment;
  if (!pending?.order) {
    root.innerHTML = `
      <div class="hero"><h1>Payment</h1><p>No pending payment</p></div>
      <div class="panel"><button class="btn btn-primary" id="to-cart">Go to cart</button></div>`;
    document.getElementById("to-cart").onclick = () => navigate("cart");
    return;
  }

  const order = pending.order;
  const payment = order.payment || {};
  const method = pending.payment_method || payment.provider || "card";
  const intentId =
    payment.stripe_payment_intent_id ||
    (pending.client_secret || "").split("_secret")[0] ||
    `${method}_sim`;
  const methodLabel = (PAY_METHODS.find((m) => m.id === method) || {}).label || method;

  let formHtml = "";
  if (method === "card") {
    formHtml = `
      <div class="field"><label>Cardholder name</label><input id="card-name" value="Test Shopper" /></div>
      <div class="field"><label>Card number</label><input id="card-num" value="4242 4242 4242 4242" maxlength="19" /></div>
      <div class="pay-row">
        <div class="field"><label>Expiry</label><input id="card-exp" value="12/30" /></div>
        <div class="field"><label>CVC</label><input id="card-cvc" value="123" maxlength="4" /></div>
      </div>`;
  } else if (method === "upi") {
    formHtml = `
      <div class="field"><label>UPI ID used</label><input id="pay-ref" value="shopper@oksbi" /></div>
      <p class="muted">Approve the collect request in your UPI app, then confirm.</p>`;
  } else if (method === "netbanking") {
    formHtml = `
      <div class="field"><label>Bank login ID (sandbox)</label><input id="pay-ref" value="demo_user" /></div>
      <p class="muted">Authorize the net-banking transaction, then confirm.</p>`;
  } else if (method === "wallet") {
    formHtml = `
      <div class="field"><label>Wallet mobile</label><input id="pay-ref" value="9999999999" /></div>
      <p class="muted">Approve wallet debit, then confirm.</p>`;
  } else {
    formHtml = `<p class="muted">Confirm to place your Cash on Delivery order. Pay the delivery partner in cash.</p>`;
  }

  root.innerHTML = `
    <div class="hero">
      <h1>Payment gateway</h1>
      <p>${escapeHtml(methodLabel)} · Order ${escapeHtml(order.order_number)}</p>
    </div>
    <div class="checkout-grid">
      <div class="panel pay-card">
        <div class="pay-brand">SmartCart Pay · ${escapeHtml(methodLabel)}</div>
        <p class="muted">${pending.payment_instructions || escapeHtml(pending.message || "")}</p>
        <div class="pay-amount">${money(order.total_amount)}</div>
        ${formHtml}
        <div class="auth-error" id="pay-error"></div>
        <button class="btn btn-primary btn-block" id="pay-success">
          ${method === "cod" ? "Confirm COD order" : `Pay ${money(order.total_amount)}`}
        </button>
        ${
          method !== "cod"
            ? `<button class="btn btn-danger btn-block" id="pay-fail" style="margin-top:0.5rem">Simulate payment failure</button>`
            : ""
        }
        <p class="muted" style="margin-top:0.75rem;font-size:0.82rem">Sandbox gateway — after success you can download the bill/invoice.</p>
      </div>
      <div class="panel">
        <h2>Order ${escapeHtml(order.order_number)}</h2>
        <div class="summary-line"><span>Method</span><span>${escapeHtml(methodLabel)}</span></div>
        <div class="summary-line"><span>Status</span><span>${escapeHtml(order.status)}</span></div>
        <div class="summary-line"><span>Payment</span><span>${escapeHtml(order.payment_status || "pending")}</span></div>
        <div class="totals">
          <div class="row grand"><span>Total</span><span>${money(order.total_amount)}</span></div>
        </div>
        ${(order.items || [])
          .map(
            (it) =>
              `<div class="summary-line"><span>${escapeHtml(it.product_name)} × ${it.quantity}</span><span>${money(it.line_total)}</span></div>`
          )
          .join("")}
      </div>
    </div>`;

  async function confirmPayment(success, failure_reason = null) {
    const err = document.getElementById("pay-error");
    if (err) err.textContent = "";
    const ref = document.getElementById("pay-ref")?.value?.trim() || null;
    try {
      const confirmed = await api("POST", `/payments/orders/${order.id}/confirm`, {
        payment_intent_id: intentId,
        success,
        failure_reason,
        payment_reference: ref,
      });
      state.pendingPayment = null;
      setCoupon("");
      state.lastOrder = confirmed;
      await refreshCartSummary();
      if (confirmed.status === "paid") {
        toast(method === "cod" ? "COD order placed" : "Payment successful");
        navigate("confirmation");
      } else {
        toast("Payment failed — order cancelled", "error");
        navigate("orders");
      }
    } catch (e) {
      if (err) err.textContent = e.message;
      toast(e.message, "error");
    }
  }

  document.getElementById("pay-success").onclick = () => confirmPayment(true);
  const failBtn = document.getElementById("pay-fail");
  if (failBtn) failBtn.onclick = () => confirmPayment(false, `${methodLabel} declined (sandbox)`);
}

function viewConfirmation() {
  const root = document.getElementById("app");
  const order = state.lastOrder;
  if (!order) {
    navigate("orders");
    return;
  }
  const method = (order.payment && order.payment.provider) || "card";
  const methodLabel = (PAY_METHODS.find((m) => m.id === method) || {}).label || method;
  root.innerHTML = `
    <div class="hero">
      <h1>Order confirmed</h1>
      <p>Bill ready · continue shopping or download invoice</p>
    </div>
    <div class="panel confirm-box">
      <div class="confirm-check">✓</div>
      <h2>Order ${escapeHtml(order.order_number)}</h2>
      <p class="muted">Status: <strong>${escapeHtml(order.status)}</strong> ·
        Payment: <strong>${escapeHtml(order.payment_status || "succeeded")}</strong> ·
        Method: <strong>${escapeHtml(methodLabel)}</strong></p>
      <div class="pay-amount" style="margin:1rem 0">${money(order.total_amount)}</div>
      <div class="btn-row" style="justify-content:center;flex-wrap:wrap">
        <button class="btn btn-primary" id="dl-bill">Download bill (PDF)</button>
        <button class="btn btn-ghost" id="see-orders">View orders</button>
        <button class="btn btn-ghost" id="keep-shop">Continue shopping</button>
      </div>
    </div>`;
  document.getElementById("dl-bill").onclick = () => downloadBill(order.id, order.order_number);
  document.getElementById("see-orders").onclick = () => navigate("orders");
  document.getElementById("keep-shop").onclick = () => navigate("shop");
}

async function viewOrders() {
  const root = document.getElementById("app");
  if (!state.token) {
    navigate("account");
    return;
  }
  const isAdm = isAdmin();
  root.innerHTML = `<div class="hero"><h1>${isAdm ? "All orders & bills" : "Orders"}</h1>
    <p>${isAdm ? "Admin can download bills for any order" : "Track purchases, pay pending, download bills"}</p></div>
    <div class="panel" id="orders">Loading…</div>`;
  try {
    const orders = isAdm
      ? await api("GET", "/admin/orders", null, { limit: 50 })
      : await api("GET", "/orders");
    const list = Array.isArray(orders) ? orders : orders.items || [];
    const el = document.getElementById("orders");
    if (!list.length) {
      el.innerHTML = `<p class="muted">No orders yet.</p><button class="btn btn-primary" id="shop">Start shopping</button>`;
      document.getElementById("shop").onclick = () => navigate("shop");
      return;
    }
    el.innerHTML = `
      <table class="table">
        <thead><tr><th>Order</th><th>Status</th><th>Method</th><th>Payment</th><th>Total</th><th>Date</th><th></th></tr></thead>
        <tbody>
          ${list
            .map((o) => {
              const pay = o.payment || {};
              const method = pay.provider || "—";
              const canPay =
                o.status === "pending" &&
                (o.payment_status === "pending" || !o.payment_status);
              return `<tr>
              <td>${escapeHtml(o.order_number || o.id)}</td>
              <td><span class="status-pill ${escapeHtml(o.status)}">${escapeHtml(o.status)}</span></td>
              <td>${escapeHtml(method)}</td>
              <td>${escapeHtml(o.payment_status || pay.status || "—")}</td>
              <td>${money(o.total_amount)}</td>
              <td class="muted">${escapeHtml((o.order_date || o.created_at || "").toString().slice(0, 10))}</td>
              <td class="btn-row">
                <button class="btn btn-ghost" data-bill="${o.id}" data-num="${escapeHtml(o.order_number || o.id)}">Bill</button>
                ${
                  canPay
                    ? `<button class="btn btn-primary" data-pay="${o.id}">Pay</button>`
                    : ""
                }
              </td>
            </tr>`;
            })
            .join("")}
        </tbody>
      </table>`;
    el.querySelectorAll("[data-bill]").forEach((b) =>
      b.addEventListener("click", () => downloadBill(b.dataset.bill, b.dataset.num))
    );
    el.querySelectorAll("[data-pay]").forEach((b) =>
      b.addEventListener("click", () => {
        const ord = list.find((x) => String(x.id) === String(b.dataset.pay));
        state.pendingPayment = {
          order: ord,
          client_secret: (ord.payment || {}).stripe_client_secret,
          publishable_key: "",
          simulated: true,
          payment_method: (ord.payment || {}).provider || "card",
          message: "Complete pending payment",
          payment_instructions: "Confirm to finish payment and generate your bill.",
        };
        navigate("payment");
      })
    );
  } catch (e) {
    toast(e.message, "error");
  }
}

function viewAccount() {
  const root = document.getElementById("app");

  if (state.user) {
    const name = state.user.name || state.user.full_name || "User";
    const role = (state.user.role || "customer").toLowerCase();
    root.innerHTML = `
      <div class="hero">
        <h1>My Account</h1>
        <p>You are signed in as ${escapeHtml(role)}</p>
      </div>
      <div class="panel profile-card">
        <h2>${escapeHtml(name)}</h2>
        <p class="muted">User ID · ${escapeHtml(state.user.email || "")}</p>
        <span class="role-pill ${role === "admin" ? "admin" : "customer"}">${escapeHtml(role)}</span>
        <div class="btn-row" style="margin-top:1rem">
          <button class="btn btn-primary" id="go-shop">Continue shopping</button>
          ${isAdmin() ? '<button class="btn btn-ghost" id="go-admin">Admin Dashboard</button>' : ""}
          <button class="btn btn-danger" id="do-logout">Logout</button>
        </div>
      </div>`;
    document.getElementById("go-shop").onclick = () => navigate("shop");
    const goAdmin = document.getElementById("go-admin");
    if (goAdmin) goAdmin.onclick = () => navigate("admin");
    document.getElementById("do-logout").onclick = () => {
      clearAuth();
      toast("Logged out");
      viewAccount();
      renderChrome();
    };
    return;
  }

  root.innerHTML = `
    <div class="hero">
      <h1>Login / Register</h1>
      <p>Sign in as guest or admin · or create a new guest account</p>
    </div>

    <div class="demo-box">
      <strong>Admin demo credentials</strong><br />
      User ID: <code>admin@smartcart.com</code> &nbsp;·&nbsp;
      Password: <code>Admin@12345</code>
      <div class="btn-row" style="margin-top:0.65rem">
        <button class="btn btn-ghost" type="button" id="fill-admin">Use admin login</button>
      </div>
    </div>

    <div class="auth-tabs">
      <button class="auth-tab active" type="button" data-tab="login">Login</button>
      <button class="auth-tab" type="button" data-tab="register">New guest registration</button>
    </div>

    <div class="panel" id="panel-login">
      <h2>Sign in</h2>
      <p class="muted" style="margin-bottom:0.85rem">Works for both guest (customer) and admin accounts.</p>
      <div class="field">
        <label>User ID (Email)</label>
        <input id="login-email" type="email" autocomplete="username" placeholder="you@example.com" />
      </div>
      <div class="field">
        <label>Password</label>
        <input id="login-pass" type="password" autocomplete="current-password" placeholder="••••••••" />
      </div>
      <div class="auth-error" id="login-error"></div>
      <button class="btn btn-primary btn-block" id="btn-login">Login</button>
    </div>

    <div class="panel hidden" id="panel-register">
      <h2>Create guest account</h2>
      <p class="muted" style="margin-bottom:0.85rem">Register a new customer with a User ID and password.</p>
      <div class="field">
        <label>Full name</label>
        <input id="reg-name" autocomplete="name" placeholder="Jane Shopper" />
      </div>
      <div class="field">
        <label>User ID (Email)</label>
        <input id="reg-email" type="email" autocomplete="username" placeholder="jane@example.com" />
      </div>
      <div class="field">
        <label>Phone (optional)</label>
        <input id="reg-phone" type="tel" placeholder="+1 555 0100" />
      </div>
      <div class="field">
        <label>Password</label>
        <input id="reg-pass" type="password" autocomplete="new-password" placeholder="Min. 8 characters" />
      </div>
      <div class="field">
        <label>Confirm password</label>
        <input id="reg-pass2" type="password" autocomplete="new-password" />
      </div>
      <div class="auth-error" id="reg-error"></div>
      <button class="btn btn-primary btn-block" id="btn-reg">Create guest account</button>
    </div>`;

  const showTab = (tab) => {
    document.querySelectorAll(".auth-tab").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === tab);
    });
    document.getElementById("panel-login").classList.toggle("hidden", tab !== "login");
    document.getElementById("panel-register").classList.toggle("hidden", tab !== "register");
  };

  document.querySelectorAll(".auth-tab").forEach((b) => {
    b.onclick = () => showTab(b.dataset.tab);
  });

  document.getElementById("fill-admin").onclick = () => {
    showTab("login");
    document.getElementById("login-email").value = "admin@smartcart.com";
    document.getElementById("login-pass").value = "Admin@12345";
    document.getElementById("login-error").textContent = "";
    toast("Admin credentials filled — click Login");
  };

  document.getElementById("btn-login").onclick = async () => {
    const err = document.getElementById("login-error");
    err.textContent = "";
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-pass").value;
    if (!email || !password) {
      err.textContent = "Enter User ID and password.";
      return;
    }
    try {
      const data = await api("POST", "/auth/login", { email, password });
      saveAuth(data);
      const role = (data.user?.role || "customer").toLowerCase();
      toast(role === "admin" ? "Welcome, Admin" : "Welcome back");
      navigate(role === "admin" ? "admin" : "shop");
    } catch (e) {
      err.textContent = e.message;
      toast(e.message, "error");
    }
  };

  document.getElementById("btn-reg").onclick = async () => {
    const err = document.getElementById("reg-error");
    err.textContent = "";
    const full_name = document.getElementById("reg-name").value.trim();
    const email = document.getElementById("reg-email").value.trim();
    const phone = document.getElementById("reg-phone").value.trim();
    const password = document.getElementById("reg-pass").value;
    const password2 = document.getElementById("reg-pass2").value;

    if (full_name.length < 2) {
      err.textContent = "Enter your full name.";
      return;
    }
    if (!email) {
      err.textContent = "Enter a User ID (email).";
      return;
    }
    if (password.length < 8) {
      err.textContent = "Password must be at least 8 characters.";
      return;
    }
    if (password !== password2) {
      err.textContent = "Passwords do not match.";
      return;
    }

    try {
      const payload = { full_name, email, password };
      if (phone) payload.phone = phone;
      const data = await api("POST", "/auth/register", payload);
      saveAuth(data);
      toast("Guest account created — you are signed in");
      navigate("shop");
    } catch (e) {
      err.textContent = e.message;
      toast(e.message, "error");
    }
  };

  // Submit on Enter
  document.getElementById("login-pass").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("btn-login").click();
  });
  document.getElementById("reg-pass2").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("btn-reg").click();
  });
}

async function viewAdmin() {
  if (!isAdmin()) {
    toast("Admin only", "error");
    navigate("shop");
    return;
  }
  const root = document.getElementById("app");
  root.innerHTML = `
    <div class="hero"><h1>Admin Dashboard</h1><p>Revenue · Orders · Inventory · Coupons</p></div>
    <div class="btn-row" style="margin-bottom:1rem">
      <button class="btn btn-primary" id="go-catalog">Manage Products</button>
      <button class="btn btn-ghost" id="go-shop-admin">View Shop</button>
    </div>
    <div id="kpis" class="kpi-row"><div class="muted">Loading…</div></div>
    <div class="section-title">Top Products</div>
    <div class="panel" id="top"></div>
    <div class="section-title">Low Stock</div>
    <div class="panel" id="low"></div>
    <div class="section-title">Coupons</div>
    <div class="panel" id="coupons"></div>
    <div class="section-title">Inventory</div>
    <div class="panel" id="inv"></div>`;
  document.getElementById("go-catalog").onclick = () => navigate("catalog");
  document.getElementById("go-shop-admin").onclick = () => navigate("shop");
  try {
    const dash = await api("GET", "/analytics/dashboard");
    state.dash = dash;
    const k = dash.kpis || {};
    document.getElementById("kpis").innerHTML = [
      ["Today's Revenue", money(k.today_revenue), ""],
      ["Monthly Revenue", money(k.monthly_revenue), "sky"],
      ["Total Orders", k.total_orders ?? 0, "coral"],
      ["Users", k.users ?? 0, "amber"],
      ["Pending Orders", k.pending_orders ?? 0, "amber"],
      ["Cancelled Orders", k.cancelled_orders ?? 0, "coral"],
      ["Low Stock", k.low_stock_count ?? 0, "lime"],
      ["Active Coupons", k.active_coupons ?? 0, "sky"],
    ]
      .map(
        ([label, value, tone]) =>
          `<div class="kpi ${tone}"><div class="label">${label}</div><div class="value">${value}</div></div>`
      )
      .join("");

    const table = (rows, cols) => {
      if (!rows || !rows.length) return `<p class="muted">Nothing to show.</p>`;
      const keys = cols || Object.keys(rows[0]);
      return `<table class="table"><thead><tr>${keys.map((k) => `<th>${escapeHtml(k)}</th>`).join("")}</tr></thead>
        <tbody>${rows
          .map(
            (r) =>
              `<tr>${keys.map((k) => `<td>${escapeHtml(r[k] ?? "")}</td>`).join("")}</tr>`
          )
          .join("")}</tbody></table>`;
    };

    document.getElementById("top").innerHTML = table(dash.top_products, ["name", "quantity", "revenue"]);
    document.getElementById("low").innerHTML = table(dash.low_stock);
    document.getElementById("coupons").innerHTML = table(dash.coupons, [
      "code",
      "discount",
      "coupon_type",
      "expiry",
      "active",
      "used_count",
    ]);
    const inv = dash.inventory || {};
    document.getElementById("inv").innerHTML = `
      <p class="muted" style="margin-bottom:0.75rem">
        Products: <strong>${inv.total_products ?? 0}</strong> ·
        Low stock: <strong>${inv.low_stock_count ?? 0}</strong> ·
        Out of stock: <strong>${inv.out_of_stock_count ?? 0}</strong>
      </p>
      ${table(inv.items)}`;
  } catch (e) {
    toast(e.message, "error");
  }
}

const IMAGE_PRESETS = [
  {
    label: "Headphones",
    url: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600",
  },
  {
    label: "Phone",
    url: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600",
  },
  {
    label: "Laptop",
    url: "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600",
  },
  {
    label: "Watch",
    url: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600",
  },
  {
    label: "Sneakers",
    url: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600",
  },
  {
    label: "Speaker",
    url: "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600",
  },
];

async function viewCatalog() {
  if (!isAdmin()) {
    toast("Admin only", "error");
    navigate("shop");
    return;
  }
  const root = document.getElementById("app");
  root.innerHTML = `
    <div class="hero">
      <h1>Manage Products</h1>
      <p>Add categories & products — they appear on the shop for cart, checkout, and payment</p>
    </div>
    <div class="checkout-grid">
      <div class="panel">
        <h2>Add product</h2>
        <div class="field">
          <label>Product name</label>
          <input id="p-name" placeholder="Galaxy Phone Case" />
        </div>
        <div class="field">
          <label>SKU</label>
          <input id="p-sku" placeholder="MB-CASE-001" />
        </div>
        <div class="field">
          <label>Description</label>
          <textarea id="p-desc" placeholder="Product details for shoppers…"></textarea>
        </div>
        <div class="pay-row">
          <div class="field">
            <label>Price (USD)</label>
            <input id="p-price" type="number" min="0.01" step="0.01" placeholder="49.99" />
          </div>
          <div class="field">
            <label>Stock</label>
            <input id="p-stock" type="number" min="0" step="1" value="25" />
          </div>
        </div>
        <div class="field">
          <label>Category</label>
          <select id="p-cat"></select>
        </div>
        <div class="field">
          <label>Image URL</label>
          <input id="p-image" placeholder="https://…" />
          <div class="preset-row" id="img-presets"></div>
          <img id="p-preview" class="img-preview hidden" alt="Preview" />
        </div>
        <label class="check-row">
          <input type="checkbox" id="p-featured" /> Featured on shop
        </label>
        <div class="auth-error" id="p-error"></div>
        <button class="btn btn-primary btn-block" id="p-save">Add product to shop</button>
      </div>

      <div>
        <div class="panel">
          <h2>Add category</h2>
          <div class="field">
            <label>Category name</label>
            <input id="c-name" placeholder="Mobile, Electronics, Beauty…" />
          </div>
          <div class="field">
            <label>Description</label>
            <input id="c-desc" placeholder="Short description" />
          </div>
          <div class="auth-error" id="c-error"></div>
          <button class="btn btn-ghost btn-block" id="c-save">Create category</button>
          <div id="cat-list" class="muted" style="margin-top:0.85rem"></div>
        </div>
        <div class="panel" style="margin-top:1rem">
          <h2>Shop catalog</h2>
          <div id="admin-products"><div class="muted">Loading…</div></div>
        </div>
      </div>
    </div>`;

  const presets = document.getElementById("img-presets");
  presets.innerHTML = IMAGE_PRESETS.map(
    (p) =>
      `<button type="button" class="btn btn-ghost preset-btn" data-url="${escapeHtml(p.url)}">${escapeHtml(p.label)}</button>`
  ).join("");
  presets.querySelectorAll("[data-url]").forEach((b) => {
    b.onclick = () => {
      document.getElementById("p-image").value = b.dataset.url;
      updatePreview();
    };
  });

  function updatePreview() {
    const url = document.getElementById("p-image").value.trim();
    const img = document.getElementById("p-preview");
    if (url) {
      img.src = url;
      img.classList.remove("hidden");
    } else {
      img.classList.add("hidden");
    }
  }
  document.getElementById("p-image").addEventListener("input", updatePreview);

  async function loadCategories() {
    const cats = await api("GET", "/categories", null, { active_only: false });
    state.categories = cats;
    const sel = document.getElementById("p-cat");
    sel.innerHTML = `<option value="">Select category</option>` +
      cats.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
    document.getElementById("cat-list").innerHTML =
      cats.map((c) => `<span class="chip">${escapeHtml(c.name)}</span>`).join(" ") ||
      "No categories yet.";
  }

  async function loadProducts() {
    const data = await api("GET", "/products", null, {
      page: 1,
      page_size: 50,
      active_only: false,
    });
    const items = data.items || [];
    const box = document.getElementById("admin-products");
    if (!items.length) {
      box.innerHTML = `<p class="muted">No products yet — add one on the left.</p>`;
      return;
    }
    box.innerHTML = items
      .map(
        (p) => `
      <div class="admin-product-row">
        <img src="${escapeHtml(p.image_url || p.image || "")}" alt="" />
        <div>
          <strong>${escapeHtml(p.name)}</strong>
          <div class="muted">${escapeHtml((p.category && p.category.name) || "Uncategorized")} · ${money(p.price)} · stock ${p.stock_quantity ?? p.stock ?? 0}</div>
        </div>
        <div class="btn-row">
          <button class="btn btn-ghost" data-view="${p.id}">View</button>
          <button class="btn btn-danger" data-del="${p.id}">Delete</button>
        </div>
      </div>`
      )
      .join("");
    box.querySelectorAll("[data-view]").forEach((b) =>
      b.addEventListener("click", () => navigate("product", { productId: Number(b.dataset.view) }))
    );
    box.querySelectorAll("[data-del]").forEach((b) =>
      b.addEventListener("click", async () => {
        if (!confirm("Delete this product from the shop?")) return;
        try {
          await api("DELETE", `/products/${b.dataset.del}`);
          toast("Product deleted");
          loadProducts();
        } catch (e) {
          toast(e.message, "error");
        }
      })
    );
  }

  document.getElementById("c-save").onclick = async () => {
    const err = document.getElementById("c-error");
    err.textContent = "";
    const name = document.getElementById("c-name").value.trim();
    const description = document.getElementById("c-desc").value.trim();
    if (name.length < 2) {
      err.textContent = "Enter a category name.";
      return;
    }
    try {
      await api("POST", "/categories", { name, description: description || null, is_active: true });
      toast(`Category “${name}” created`);
      document.getElementById("c-name").value = "";
      document.getElementById("c-desc").value = "";
      await loadCategories();
    } catch (e) {
      err.textContent = e.message;
      toast(e.message, "error");
    }
  };

  document.getElementById("p-save").onclick = async () => {
    const err = document.getElementById("p-error");
    err.textContent = "";
    const name = document.getElementById("p-name").value.trim();
    const sku = document.getElementById("p-sku").value.trim();
    const description = document.getElementById("p-desc").value.trim();
    const price = Number(document.getElementById("p-price").value);
    const stock = Number(document.getElementById("p-stock").value);
    const category_id = document.getElementById("p-cat").value
      ? Number(document.getElementById("p-cat").value)
      : null;
    const image_url = document.getElementById("p-image").value.trim() || null;
    const is_featured = document.getElementById("p-featured").checked;

    if (name.length < 2) {
      err.textContent = "Enter a product name.";
      return;
    }
    if (sku.length < 2) {
      err.textContent = "Enter a SKU code.";
      return;
    }
    if (!(price > 0)) {
      err.textContent = "Enter a valid price.";
      return;
    }
    if (!category_id) {
      err.textContent = "Select a category (or create one first).";
      return;
    }

    try {
      const created = await api("POST", "/products", {
        name,
        sku,
        description: description || null,
        price,
        stock_quantity: Number.isFinite(stock) ? stock : 0,
        category_id,
        image_url,
        is_featured,
        is_active: true,
      });
      toast(`“${created.name}” added to shop`);
      document.getElementById("p-name").value = "";
      document.getElementById("p-sku").value = "";
      document.getElementById("p-desc").value = "";
      document.getElementById("p-price").value = "";
      document.getElementById("p-stock").value = "25";
      document.getElementById("p-image").value = "";
      document.getElementById("p-featured").checked = false;
      updatePreview();
      await loadProducts();
    } catch (e) {
      err.textContent = e.message;
      toast(e.message, "error");
    }
  };

  try {
    await loadCategories();
    await loadProducts();
  } catch (e) {
    toast(e.message, "error");
  }
}

function boot() {
  try {
    const brand = document.getElementById("brand-home");
    if (brand) {
      brand.addEventListener("click", (e) => {
        e.preventDefault();
        navigate("shop");
      });
    }
    document.querySelectorAll(".nav-btn[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => navigate(btn.dataset.page));
    });
    setCartCount(state.cartCount);
    renderChrome();
    refreshCartSummary().finally(() => navigate("shop"));
  } catch (err) {
    const root = document.getElementById("app");
    if (root) {
      root.innerHTML = `<div class="panel"><p class="muted">UI failed to start: ${escapeHtml(String(err))}</p></div>`;
    }
    console.error(err);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
