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
  productsCacheKey: "",
  productsFetchedAt: 0,
  categories: [],
  categoriesLoaded: false,
  cart: null,
  cartFetchedAt: 0,
  cartCount: Number(localStorage.getItem("sc_cart_count") || 0),
  couponCode: localStorage.getItem("sc_coupon") || "",
  pendingPayment: null,
  lastOrder: null,
  dash: null,
  productId: null,
  authValidatedAt: 0,
  checkoutDraft: null,
  navSeq: 0,
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
    state.cartFetchedAt = Date.now();
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

/** Prefer smaller Unsplash thumbs so shop/cart LCP is not blocked by 600px remote images */
function thumbUrl(url) {
  if (!url) return "";
  try {
    const u = new URL(url, window.location.origin);
    if (u.hostname.includes("images.unsplash.com") || u.hostname.includes("unsplash.com")) {
      u.searchParams.set("w", "400");
      u.searchParams.set("q", "55");
      u.searchParams.set("auto", "format");
      u.searchParams.set("fit", "crop");
      return u.toString();
    }
  } catch {
    /* keep original */
  }
  return url;
}

async function downloadBill(orderId, orderNumber) {
  if (!state.token) {
    toast(t("bill.signin"), "error");
    return;
  }
  try {
    const url = `${API}/orders/${orderId}/invoice`;
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    if (!res.ok) {
      const bodyText = await res.text();
      throw new Error(bodyText || t("bill.fail"));
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `bill-${orderNumber || orderId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
    toast(t("bill.ok"));
  } catch (e) {
    toast(e.message, "error");
  }
}

function PAY_METHODS() { return payMethods(); }


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
  state.authValidatedAt = Date.now();
  localStorage.setItem("sc_token", state.token);
  localStorage.setItem("sc_refresh", state.refresh);
  localStorage.setItem("sc_user", JSON.stringify(state.user));
  renderChrome();
}

async function refreshUserProfile() {
  if (!state.token) return null;
  try {
    const user = await api("GET", "/users/me");
    state.user = user;
    localStorage.setItem("sc_user", JSON.stringify(user));
    renderChrome();
    return user;
  } catch {
    return null;
  }
}

function clearAuth() {
  state.token = "";
  state.refresh = "";
  state.user = null;
  state.cart = null;
  state.pendingPayment = null;
  state.authValidatedAt = 0;
  localStorage.removeItem("sc_token");
  localStorage.removeItem("sc_refresh");
  localStorage.removeItem("sc_user");
  setCartCount(0);
  renderChrome();
}

function isAdmin() {
  return state.user && (state.user.role === "admin" || state.user.role === "Admin");
}

let _refreshInFlight = null;

async function refreshAccessToken() {
  if (!state.refresh) return false;
  if (_refreshInFlight) return _refreshInFlight;
  _refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: state.refresh }),
      });
      const text = await res.text();
      let data = null;
      if (text) {
        try {
          data = JSON.parse(text);
        } catch {
          data = null;
        }
      }
      if (!res.ok) return false;
      saveAuth(data);
      return true;
    } catch {
      return false;
    } finally {
      _refreshInFlight = null;
    }
  })();
  return _refreshInFlight;
}

async function ensureAuthSession(force = false) {
  if (!state.token) return false;
  const fresh = Date.now() - (state.authValidatedAt || 0) < 60000;
  if (!force && fresh && state.user) return true;
  try {
    const user = await api("GET", "/auth/validate", null, null, { skipAuthRetry: true });
    state.user = user;
    state.authValidatedAt = Date.now();
    localStorage.setItem("sc_user", JSON.stringify(user));
    renderChrome();
    return true;
  } catch {
    const ok = await refreshAccessToken();
    if (!ok) {
      clearAuth();
      state.authValidatedAt = 0;
      return false;
    }
    try {
      const user = await api("GET", "/auth/validate", null, null, { skipAuthRetry: true });
      state.user = user;
      state.authValidatedAt = Date.now();
      localStorage.setItem("sc_user", JSON.stringify(user));
      renderChrome();
      return true;
    } catch {
      clearAuth();
      state.authValidatedAt = 0;
      return false;
    }
  }
}

function parseApiError(data, status) {
  let detail = `Request failed (${status})`;
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
  return typeof detail === "string" ? detail : JSON.stringify(detail);
}

async function api(method, path, body, params, opts) {
  const options = opts || {};
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
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (res.status === 401 && !options.skipAuthRetry && !path.startsWith("/auth/login") && !path.startsWith("/auth/register") && !path.startsWith("/auth/refresh")) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return api(method, path, body, params, { ...options, skipAuthRetry: true });
    }
    clearAuth();
    const detail = parseApiError(data, res.status);
    const err = new Error(detail || t("auth.sessionExpired"));
    err.status = 401;
    err.authFailed = true;
    throw err;
  }

  if (!res.ok) {
    const detail = parseApiError(data, res.status);
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return data;
}

function renderChrome() {
  const box = document.getElementById("user-box");
  const navAccount = document.getElementById("nav-account");
  if (navAccount) {
    navAccount.textContent = state.user ? t("nav.account") : t("nav.login");
  }
  if (state.user) {
    const name = state.user.name || state.user.full_name || t("user.user");
    const role = (state.user.role || "customer").toLowerCase();
    const pts = Number(state.user.loyalty_points || 0);
    const loyaltyChip =
      role === "customer"
        ? `<span class="loyalty-chip">${pts} ${t("loyalty.pts")}</span>`
        : "";
    box.innerHTML = `
      <div><strong>${escapeHtml(name)}</strong></div>
      <div class="email">${escapeHtml(state.user.email || "")}</div>
      <span class="role-pill ${role === "admin" ? "admin" : "customer"}">${escapeHtml(tRole(role))}</span>
      ${loyaltyChip}
      <button class="nav-btn" style="margin-top:0.6rem" id="btn-logout">${t("user.logout")}</button>
    `;
    document.getElementById("btn-logout").onclick = () => {
      clearAuth();
      toast(t("account.loggedOut"));
      navigate("account");
    };
  } else {
    box.innerHTML = `
      <div class="email">${t("user.guest")}</div>
      <button class="nav-btn" style="margin-top:0.6rem" id="btn-goto-login">${t("user.loginRegister")}</button>
    `;
    document.getElementById("btn-goto-login").onclick = () => navigate("account");
  }
  document.getElementById("nav-admin").classList.toggle("hidden", !isAdmin());
  const navCatalog = document.getElementById("nav-catalog");
  if (navCatalog) navCatalog.classList.toggle("hidden", !isAdmin());
  document.querySelectorAll(".nav-btn[data-page]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === state.page);
  });
  if (typeof applyStaticI18n === "function") applyStaticI18n();
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
  state.navSeq = (state.navSeq || 0) + 1;
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

function productCardHtml(p) {
  return `
        <article class="card">
          ${
            p.image_url || p.image
              ? `<img src="${escapeHtml(thumbUrl(p.image_url || p.image))}" alt="" loading="lazy" decoding="async" width="400" height="240" />`
              : ""
          }
          ${p.is_featured ? `<span class="badge">${t("shop.featured")}</span>` : ""}
          <h3>${escapeHtml(p.name)}</h3>
          <div class="muted">${escapeHtml(tCat((p.category && p.category.name) || ""))}</div>
          <div class="price">${money(p.price)}</div>
          <div class="muted">${t("shop.stock")}: ${p.stock_quantity ?? p.stock ?? 0}</div>
          <div class="btn-row">
            <button class="btn btn-ghost" data-view="${p.id}">${t("shop.details")}</button>
            <button class="btn btn-primary" data-add="${p.id}">${t("shop.add")}</button>
          </div>
        </article>`;
}

function bindProductGrid(grid) {
  if (!grid) return;
  grid.querySelectorAll("[data-view]").forEach((b) =>
    b.addEventListener("click", () => navigate("product", { productId: Number(b.dataset.view) }))
  );
  grid.querySelectorAll("[data-add]").forEach((b) =>
    b.addEventListener("click", () => addToCart(Number(b.dataset.add)))
  );
}

async function viewShop() {
  const root = document.getElementById("app");
  const seq = state.navSeq;
  root.innerHTML = `
    <div class="hero">
      <h1 class="brand-title" id="hero-home" title="${t("brand.goShop")}" role="link" tabindex="0">SmartCart</h1>
      <p>${t("shop.tagline")}</p>
      <div class="links-row">
        <a href="/docs">${t("shop.docs")}</a>
        <a href="/health">${t("shop.health")}</a>
      </div>
    </div>
    <div class="toolbar">
      <label>${t("shop.search")}<input id="q" placeholder="${t("shop.searchPh")}" /></label>
      <label>${t("shop.category")}
        <select id="cat"><option value="">${t("shop.all")}</option></select>
      </label>
      <label>&nbsp;<button class="btn btn-primary" id="btn-search">${t("shop.search")}</button></label>
    </div>
    <div id="product-grid" class="grid">${
      state.products.length && !state.productsCacheKey
        ? state.products.map(productCardHtml).join("")
        : state.products.length && state.productsCacheKey === "|"
          ? state.products.map(productCardHtml).join("")
          : `<div class="muted">${t("shop.loading")}</div>`
    }</div>
  `;

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

  // Paint cached default shop grid immediately
  const gridEl = document.getElementById("product-grid");
  if (state.products.length && (!state.productsCacheKey || state.productsCacheKey === "|")) {
    bindProductGrid(gridEl);
  }

  function fillCategories() {
    const cat = document.getElementById("cat");
    if (!cat || !state.categories) return;
    const current = cat.value;
    cat.innerHTML = `<option value="">${t("shop.all")}</option>`;
    state.categories.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = tCat(c.name);
      cat.appendChild(opt);
    });
    if (current) cat.value = current;
  }

  function renderProducts(items) {
    const grid = document.getElementById("product-grid");
    if (!grid || seq !== state.navSeq) return;
    if (!items.length) {
      grid.innerHTML = `<div class="muted">${t("shop.empty")}</div>`;
      return;
    }
    grid.innerHTML = items.map(productCardHtml).join("");
    bindProductGrid(grid);
  }

  async function load(force = false) {
    if (seq !== state.navSeq) return;
    const q = document.getElementById("q")?.value.trim() || "";
    const category_id = document.getElementById("cat")?.value || "";
    const cacheKey = `${q}|${category_id}`;
    const fresh =
      !force &&
      state.productsCacheKey === cacheKey &&
      state.products.length &&
      Date.now() - (state.productsFetchedAt || 0) < 60000;

    if (fresh) {
      renderProducts(state.products);
      return;
    }

    // Instant paint from stale cache for same filters
    if (state.productsCacheKey === cacheKey && state.products.length) {
      renderProducts(state.products);
    }

    try {
      const data = await api("GET", "/products", null, {
        page: 1,
        page_size: 24,
        active_only: true,
        q: q || undefined,
        category_id: category_id || undefined,
      });
      if (seq !== state.navSeq) return;
      state.products = data.items || [];
      state.productsCacheKey = cacheKey;
      state.productsFetchedAt = Date.now();
      renderProducts(state.products);
    } catch (e) {
      if (seq === state.navSeq) toast(e.message, "error");
    }
  }

  // Load categories + products in parallel (reuse cached categories)
  try {
    const tasks = [load()];
    if (!state.categoriesLoaded) {
      tasks.push(
        api("GET", "/categories", null, { active_only: true }).then((cats) => {
          state.categories = cats || [];
          state.categoriesLoaded = true;
          if (seq === state.navSeq) fillCategories();
        })
      );
    } else {
      fillCategories();
    }
    await Promise.all(tasks);
  } catch (e) {
    toast(e.message, "error");
  }

  let searchTimer = null;
  document.getElementById("btn-search").onclick = () => load(true);
  document.getElementById("cat").addEventListener("change", () => load(true));
  document.getElementById("q").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => load(true), 280);
  });
  document.getElementById("q").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      clearTimeout(searchTimer);
      load(true);
    }
  });
}

async function viewProduct() {
  const root = document.getElementById("app");
  root.innerHTML = `<div class="muted">${t("product.loading")}</div>`;
  try {
    const p = await api("GET", `/products/${state.productId}`);
    root.innerHTML = `
      <button class="btn btn-ghost" id="back">${t("product.back")}</button>
      <div class="panel" style="margin-top:1rem;display:grid;grid-template-columns:1fr 1fr;gap:1.25rem">
        <div>
          ${p.image_url || p.image ? `<img src="${escapeHtml(p.image_url || p.image)}" style="width:100%;border-radius:14px" alt="" loading="lazy" decoding="async" />` : ""}
        </div>
        <div>
          <h2 style="font-family:Outfit,system-ui,sans-serif;font-size:1.8rem;letter-spacing:-0.03em">${escapeHtml(p.name)}</h2>
          <div class="price" style="margin:0.5rem 0">${money(p.price)}</div>
          <p class="muted" style="margin-bottom:1rem">${escapeHtml(p.description || "No description.")}</p>
          <div class="field">
            <label>${t("product.qty")}</label>
            <input type="number" id="qty" min="1" max="50" value="1" />
          </div>
          <div class="btn-row">
            <button class="btn btn-primary" id="add">${t("product.addCart")}</button>
            <button class="btn btn-ghost" id="wish">${t("product.wishlist")}</button>
          </div>
        </div>
      </div>`;
    document.getElementById("back").onclick = () => navigate("shop");
    document.getElementById("add").onclick = () =>
      addToCart(p.id, Number(document.getElementById("qty").value || 1));
    document.getElementById("wish").onclick = async () => {
      if (!state.token) return toast(t("product.signIn"), "error");
      try {
        await api("POST", "/wishlist", { product_id: p.id });
        toast(t("product.wishlistOk"));
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
    toast(t("product.signInAdd"), "error");
    navigate("account");
    return;
  }
  // Trust JWT; api() retries on 401 — skip extra /auth/validate round-trip
  try {
    await api("POST", "/cart/items", { product_id: productId, quantity });
    await refreshCartSummary();
    toast(t("product.addOk"));
  } catch (e) {
    if (e.authFailed || e.status === 401) {
      toast(t("auth.sessionExpired"), "error");
      navigate("account");
      return;
    }
    toast(e.message, "error");
  }
}

async function viewCart() {
  const root = document.getElementById("app");
  if (!state.token) {
    root.innerHTML = `<div class="panel"><p>${t("cart.signinBefore")}<a href="#" id="go-account" style="color:var(--teal-deep);font-weight:700">${t("cart.signinLink")}</a>${t("cart.signinAfter")}</p></div>`;
    document.getElementById("go-account").onclick = (e) => {
      e.preventDefault();
      navigate("account");
    };
    return;
  }
  root.innerHTML = `
    <div class="hero">
      <h1>${t("cart.title")}</h1>
      <p>${t("cart.sub")}</p>
    </div>
    <div id="cart-body" class="panel">${
      state.cart?.items?.length ? "" : t("common.loading")
    }</div>`;

  async function setItemQuantity(itemId, quantity) {
    const id = Number(itemId);
    if (quantity < 1) {
      await api("DELETE", `/cart/items/${id}`);
      toast(t("cart.removed"));
      return;
    }
    await api("PATCH", `/cart/items/${id}`, { quantity });
  }

  const renderCartBody = (cart) => {
    const body = document.getElementById("cart-body");
    if (!body) return;
    const items = cart.items || [];
    if (!items.length) {
      body.innerHTML = `
        <p class="muted">${t("cart.empty")}</p>
        <button class="btn btn-primary" id="shop">${t("cart.continue")}</button>`;
      document.getElementById("shop").onclick = () => navigate("shop");
      return;
    }
    const couponVal = escapeHtml(state.couponCode || cart.coupon_code || "");
    body.innerHTML = `
      ${items
        .map(
          (it) => `
        <div class="cart-item" data-item-id="${it.id}">
          <img src="${escapeHtml(thumbUrl(it.product?.image_url || it.product?.image || ""))}" alt="" loading="lazy" decoding="async" />
          <div>
            <strong>${escapeHtml(it.product?.name || "Item")}</strong>
            <div class="muted">${money(it.product?.price)} ${t("cart.each")}</div>
            <div class="qty-row" role="group" aria-label="${t("cart.qty")}">
              <button type="button" class="btn qty-btn" data-dec="${it.id}" aria-label="${t("cart.qtyMinus")}" title="${t("cart.qtyMinus")}">−</button>
              <input class="qty-input" type="number" min="1" max="99" value="${it.quantity}" data-qty="${it.id}" aria-label="${t("cart.qty")}" />
              <button type="button" class="btn qty-btn" data-inc="${it.id}" aria-label="${t("cart.qtyPlus")}" title="${t("cart.qtyPlus")}">+</button>
            </div>
          </div>
          <div style="text-align:right">
            <div class="price">${money(it.line_total)}</div>
            <button type="button" class="btn btn-danger" data-rm="${it.id}" style="margin-top:0.35rem">${t("cart.remove")}</button>
          </div>
        </div>`
        )
        .join("")}
      <div class="totals">
        <div class="row"><span>${t("cart.subtotal")}</span><span>${money(cart.subtotal)}</span></div>
        <div class="row"><span>${t("cart.discount")}</span><span>-${money(cart.discount_amount)}</span></div>
        <div class="row"><span>${t("cart.shipping")}</span><span>${money(cart.shipping_amount)}</span></div>
        <div class="row"><span>${t("cart.tax")}</span><span>${money(cart.tax_amount)}</span></div>
        <div class="row grand"><span>${t("cart.total")}</span><span>${money(cart.total)}</span></div>
      </div>
      <div class="field" style="margin-top:1rem">
        <label>${t("cart.coupon")}</label>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap">
          <input id="coupon" placeholder="WELCOME10 or SAVE5" value="${couponVal}" style="flex:1" />
          <button class="btn btn-ghost" id="apply-coupon">${t("cart.apply")}</button>
        </div>
        <p class="muted" style="margin-top:0.35rem">${t("cart.couponHint")}</p>
      </div>
      <button class="btn btn-primary btn-block" id="to-checkout" style="margin-top:0.75rem">${t("cart.checkout")}</button>
    `;

    const runQtyUpdate = async (itemId, nextQty) => {
      const controls = body.querySelectorAll("[data-inc], [data-dec], [data-qty], [data-rm]");
      controls.forEach((el) => {
        el.disabled = true;
      });
      try {
        await setItemQuantity(itemId, nextQty);
        const updated = await refreshCartSummary();
        if (updated) renderCartBody(updated);
        else viewCart();
      } catch (e) {
        toast(e.message, "error");
        controls.forEach((el) => {
          el.disabled = false;
        });
      }
    };

    body.querySelectorAll("[data-rm]").forEach((b) =>
      b.addEventListener("click", async () => {
        try {
          b.disabled = true;
          await api("DELETE", `/cart/items/${b.dataset.rm}`);
          toast(t("cart.removed"));
          const updated = await refreshCartSummary();
          if (updated) renderCartBody(updated);
          else viewCart();
        } catch (e) {
          b.disabled = false;
          toast(e.message, "error");
        }
      })
    );

    body.querySelectorAll("[data-inc]").forEach((b) =>
      b.addEventListener("click", () => {
        const item = items.find((i) => String(i.id) === String(b.dataset.inc));
        runQtyUpdate(b.dataset.inc, (item?.quantity || 1) + 1);
      })
    );

    body.querySelectorAll("[data-dec]").forEach((b) =>
      b.addEventListener("click", () => {
        const item = items.find((i) => String(i.id) === String(b.dataset.dec));
        runQtyUpdate(b.dataset.dec, (item?.quantity || 1) - 1);
      })
    );

    body.querySelectorAll("[data-qty]").forEach((input) =>
      input.addEventListener("change", () => {
        const raw = Number(input.value);
        const q = Number.isFinite(raw) ? Math.floor(raw) : 1;
        if (q < 1) {
          runQtyUpdate(input.dataset.qty, 0);
          return;
        }
        runQtyUpdate(input.dataset.qty, Math.min(99, q));
      })
    );

    document.getElementById("apply-coupon").onclick = async () => {
      const code = document.getElementById("coupon").value.trim();
      if (!code) {
        toast(t("cart.enterCoupon"), "error");
        return;
      }
      try {
        const updated = await api("POST", "/cart/apply-coupon", { code });
        setCoupon(code);
        state.cart = updated;
        state.cartFetchedAt = Date.now();
        toast(t("cart.couponApplied", { code, amount: money(updated.discount_amount) }));
        renderCartBody(updated);
      } catch (e) {
        toast(e.message, "error");
      }
    };
    document.getElementById("to-checkout").onclick = () => navigate("checkout");
  };

  if (state.cart?.items) {
    renderCartBody(state.cart);
  }

  try {
    const cart = await api("GET", "/cart");
    state.cart = cart;
    state.cartFetchedAt = Date.now();
    setCartCount(cart.item_count || (cart.items || []).length || 0);
    renderCartBody(cart);
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
  const cartFresh = cart?.items?.length && Date.now() - (state.cartFetchedAt || 0) < 30000;
  if (!cartFresh) {
    try {
      cart = await api("GET", "/cart");
      state.cart = cart;
      state.cartFetchedAt = Date.now();
      setCartCount(cart.item_count || 0);
    } catch (e) {
      toast(e.message, "error");
      return;
    }
  } else {
    // Soft-refresh in background without blocking checkout UI
    api("GET", "/cart")
      .then((c) => {
        state.cart = c;
        state.cartFetchedAt = Date.now();
        setCartCount(c.item_count || 0);
      })
      .catch(() => {});
  }

  if (!cart?.items?.length) {
    root.innerHTML = `
      <div class="hero"><h1>${t("checkout.title")}</h1><p>${t("checkout.empty")}</p></div>
      <div class="panel"><button class="btn btn-primary" id="shop">${t("checkout.goShop")}</button></div>`;
    document.getElementById("shop").onclick = () => navigate("shop");
    return;
  }

  const user = state.user || {};
  const draft = state.checkoutDraft || {};
  const defaultAddr = [
    user.address_line1,
    user.address_line2,
    [user.city, user.state, user.postal_code].filter(Boolean).join(", "),
    user.country,
  ]
    .filter(Boolean)
    .join(", ");
  const shipVal = draft.ship != null ? draft.ship : defaultAddr;
  const billVal = draft.bill != null ? draft.bill : "";
  const couponVal = draft.coupon != null ? draft.coupon : state.couponCode || "";
  const notesVal = draft.notes != null ? draft.notes : "";
  const redeemVal = draft.redeem != null ? draft.redeem : "0";
  const payMethodVal = draft.payMethod || "card";
  const billSame = draft.billSame !== false;

  root.innerHTML = `
    <div class="hero">
      <h1>${t("checkout.title")}</h1>
      <p>${t("checkout.sub")}</p>
    </div>
    <div class="checkout-grid">
      <div class="panel">
        <h2>${t("checkout.shipping")}</h2>
        <div class="field">
          <label>${t("checkout.shipAddr")}</label>
          <textarea id="ship" placeholder="123 Main St, City, State, ZIP, Country">${escapeHtml(shipVal)}</textarea>
          <p class="muted" style="margin-top:0.35rem;font-size:0.82rem">${t("checkout.addrHint")}</p>
        </div>
        <div class="field">
          <label>${t("checkout.billAddr")}</label>
          <textarea id="bill" placeholder="${t("checkout.billPh")}">${escapeHtml(billVal)}</textarea>
          <label class="check-row" style="margin-top:0.45rem">
            <input type="checkbox" id="bill-same" ${billSame ? "checked" : ""} /> ${t("checkout.sameAsShip")}
          </label>
        </div>
        <div class="field">
          <label>${t("checkout.coupon")}</label>
          <input id="c_code" placeholder="WELCOME10" value="${escapeHtml(couponVal)}" />
        </div>
        <div class="field">
          <label>${t("checkout.notes")}</label>
          <input id="notes" placeholder="${t("checkout.notesPh")}" value="${escapeHtml(notesVal)}" />
        </div>
        <div class="field" id="loyalty-redeem-wrap">
          <label>${t("loyalty.redeem")}</label>
          <input id="redeem_pts" type="number" min="0" step="10" value="${escapeHtml(String(redeemVal))}" placeholder="0" />
          <p class="muted" id="loyalty-hint" style="margin-top:0.35rem"></p>
          <p class="muted" id="loyalty-earn-hint" style="margin-top:0.2rem"></p>
        </div>

        <h2 style="margin-top:1rem">${t("checkout.payMethod")}</h2>
        <div class="pay-methods" id="pay-methods">
          ${PAY_METHODS().map(
            (m) => `
            <label class="pay-method ${m.id === payMethodVal ? "active" : ""}">
              <input type="radio" name="pay_method" value="${m.id}" ${m.id === payMethodVal ? "checked" : ""} />
              <span><strong>${m.label}</strong><br/><small>${m.hint}</small></span>
            </label>`
          ).join("")}
        </div>
        <div id="method-fields"></div>

        <div class="auth-error" id="checkout-error"></div>
        <button class="btn btn-primary btn-block" id="place">${t("checkout.continue")}</button>
        <button class="btn btn-ghost btn-block" id="back-cart" style="margin-top:0.5rem">${t("checkout.back")}</button>
      </div>
      <div class="panel">
        <h2>${t("checkout.summary")}</h2>
        <div id="checkout-items">
          ${(cart.items || [])
            .map(
              (it) => `
            <div class="checkout-item" data-item-id="${it.id}">
              <img src="${escapeHtml(thumbUrl(it.product?.image_url || it.product?.image || ""))}" alt="" loading="lazy" decoding="async" />
              <div class="meta">
                <strong>${escapeHtml(it.product?.name || "Item")}</strong>
                <div class="muted">× ${it.quantity} · ${money(it.product?.price)} ${t("cart.each")}</div>
              </div>
              <div class="actions">
                <div class="price">${money(it.line_total)}</div>
                <button type="button" class="btn btn-danger btn-remove" data-rm="${it.id}">${t("checkout.removeItem")}</button>
              </div>
            </div>`
            )
            .join("")}
        </div>
        <div class="totals" style="margin-top:0.75rem">
          <div class="row"><span>${t("cart.subtotal")}</span><span id="sum-subtotal">${money(cart.subtotal)}</span></div>
          <div class="row"><span>${t("cart.discount")}</span><span id="sum-discount">-${money(cart.discount_amount)}</span></div>
          <div class="row"><span>${t("loyalty.discount")}</span><span id="sum-points">-$0.00</span></div>
          <div class="row"><span>${t("cart.shipping")}</span><span id="sum-shipping">${money(cart.shipping_amount)}</span></div>
          <div class="row"><span>${t("cart.tax")}</span><span id="sum-tax">${money(cart.tax_amount)}</span></div>
          <div class="row grand"><span>${t("checkout.totalDue")}</span><span id="sum-total">${money(cart.total)}</span></div>
        </div>
      </div>
    </div>`;

  function saveCheckoutDraft() {
    state.checkoutDraft = {
      ship: document.getElementById("ship")?.value || "",
      bill: document.getElementById("bill")?.value || "",
      coupon: document.getElementById("c_code")?.value || "",
      notes: document.getElementById("notes")?.value || "",
      redeem: document.getElementById("redeem_pts")?.value || "0",
      payMethod: document.querySelector('input[name="pay_method"]:checked')?.value || "card",
      billSame: !!document.getElementById("bill-same")?.checked,
    };
  }

  document.getElementById("checkout-items")?.querySelectorAll("[data-rm]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const itemId = btn.dataset.rm;
      btn.disabled = true;
      try {
        saveCheckoutDraft();
        await api("DELETE", `/cart/items/${itemId}`);
        toast(t("checkout.itemRemoved"));
        const updated = await refreshCartSummary();
        if (!updated?.items?.length) {
          state.checkoutDraft = null;
          toast(t("checkout.needItems"));
          navigate("cart");
          return;
        }
        viewCheckout();
      } catch (e) {
        btn.disabled = false;
        toast(e.message, "error");
      }
    });
  });

  async function refreshLoyaltyPreview() {
    const wrap = document.getElementById("loyalty-redeem-wrap");
    if (!wrap || isAdmin()) {
      if (wrap) wrap.classList.add("hidden");
      return;
    }
    const redeem = Number(document.getElementById("redeem_pts")?.value || 0);
    const coupon = document.getElementById("c_code")?.value.trim() || null;
    try {
      const prev = await api("POST", "/loyalty/preview", {
        redeem_points: redeem,
        coupon_code: coupon,
      });
      const hint = document.getElementById("loyalty-hint");
      const earnHint = document.getElementById("loyalty-earn-hint");
      const rules = prev.rules || {};
      if (hint) {
        hint.textContent = `${t("loyalty.available", { balance: prev.balance })} · ${t("loyalty.redeemHint", {
          min: rules.min_redeem_points || 100,
        })}`;
      }
      if (earnHint) {
        earnHint.textContent = t("loyalty.willEarn", { pts: prev.estimated_earn || 0 });
      }
      const ptsEl = document.getElementById("sum-points");
      const totEl = document.getElementById("sum-total");
      if (ptsEl) ptsEl.textContent = `-${money(prev.points_discount || 0)}`;
      if (totEl) totEl.textContent = money(prev.cart_total);
    } catch {
      /* ignore preview errors while typing */
    }
  }

  function renderMethodFields() {
    const method = document.querySelector('input[name="pay_method"]:checked')?.value || "card";
    const box = document.getElementById("method-fields");
    document.querySelectorAll(".pay-method").forEach((el) => {
      el.classList.toggle("active", el.querySelector("input")?.value === method);
    });
    if (method === "upi") {
      box.innerHTML = `<div class="field"><label>${t("pay.upiId")}</label><input id="upi_id" placeholder="name@upi" value="shopper@oksbi" /></div>`;
    } else if (method === "qr") {
      box.innerHTML = `<div class="field"><label>${t("pay.qrVpa")}</label><input id="upi_id" placeholder="${t("pay.qrMerchantPh")}" value="smartcart@upi" /></div>
        <p class="muted">${t("pay.qrScan")}</p>`;
    } else if (method === "netbanking") {
      box.innerHTML = `<div class="field"><label>${t("pay.bank")}</label>
        <select id="bank">
          <option>HDFC Bank</option><option>ICICI Bank</option><option>SBI</option>
          <option>Axis Bank</option><option>Kotak Mahindra</option><option>Demo Bank</option>
        </select></div>`;
    } else if (method === "wallet") {
      box.innerHTML = `<div class="field"><label>${t("pay.walletLabel")}</label>
        <select id="wallet">
          <option>PhonePe</option><option>Google Pay</option><option>Paytm</option><option>Amazon Pay</option>
        </select></div>`;
    } else if (method === "cod") {
      box.innerHTML = `<p class="muted">${t("pay.codNote")}</p>`;
    } else {
      box.innerHTML = `<p class="muted">${t("pay.cardNext")}</p>`;
    }
  }

  document.querySelectorAll('input[name="pay_method"]').forEach((r) => {
    r.addEventListener("change", renderMethodFields);
  });
  renderMethodFields();

  const shipEl = document.getElementById("ship");
  const billEl = document.getElementById("bill");
  const sameEl = document.getElementById("bill-same");
  const syncBilling = () => {
    if (sameEl?.checked && shipEl && billEl) {
      billEl.value = shipEl.value;
      billEl.readOnly = true;
    } else if (billEl) {
      billEl.readOnly = false;
    }
  };
  sameEl?.addEventListener("change", syncBilling);
  shipEl?.addEventListener("input", () => {
    if (sameEl?.checked) syncBilling();
  });
  syncBilling();

  let loyaltyTimer = null;
  document.getElementById("redeem_pts")?.addEventListener("input", () => {
    clearTimeout(loyaltyTimer);
    loyaltyTimer = setTimeout(refreshLoyaltyPreview, 300);
  });
  document.getElementById("c_code")?.addEventListener("change", refreshLoyaltyPreview);
  refreshLoyaltyPreview();

  document.getElementById("back-cart").onclick = () => {
    state.checkoutDraft = null;
    navigate("cart");
  };
  document.getElementById("place").onclick = async () => {
    const err = document.getElementById("checkout-error");
    err.textContent = "";
    saveCheckoutDraft();
    if (!(state.cart?.items?.length)) {
      err.textContent = t("checkout.needItems");
      toast(t("checkout.needItems"), "error");
      return;
    }
    let shipping_address = document.getElementById("ship").value.trim();
    let billing_address = document.getElementById("bill").value.trim();

    // If shipping is blank/short but billing is filled, use billing for shipping
    if (shipping_address.length < 10 && billing_address.length >= 10) {
      shipping_address = billing_address;
      document.getElementById("ship").value = shipping_address;
    }
    // Blank billing → same as shipping
    if (!billing_address && shipping_address.length >= 10) {
      billing_address = shipping_address;
    }

    if (shipping_address.length < 10) {
      err.textContent = t("checkout.needAddr");
      toast(t("checkout.needAddr"), "error");
      document.getElementById("ship")?.focus();
      document.getElementById("ship")?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    if (billing_address && billing_address.length < 10) {
      err.textContent = t("checkout.needBillAddr");
      toast(t("checkout.needBillAddr"), "error");
      document.getElementById("bill")?.focus();
      return;
    }

    const payment_method = document.querySelector('input[name="pay_method"]:checked')?.value || "card";
    const payment_details = {};
    if (payment_method === "upi" || payment_method === "qr") {
      payment_details.upi_id = document.getElementById("upi_id")?.value.trim() || "smartcart@upi";
    }
    if (payment_method === "netbanking") payment_details.bank = document.getElementById("bank")?.value;
    if (payment_method === "wallet") payment_details.wallet = document.getElementById("wallet")?.value;
    const redeemRaw = document.getElementById("redeem_pts")?.value;
    const redeem_points = Number.isFinite(Number(redeemRaw)) ? Math.max(0, Math.floor(Number(redeemRaw))) : 0;

    const btn = document.getElementById("place");
    btn.disabled = true;
    btn.textContent = t("checkout.creating");
    try {
      const ok = await ensureAuthSession();
      if (!ok) {
        throw new Error(t("auth.sessionExpired"));
      }
      const coupon = document.getElementById("c_code").value.trim();
      if (coupon) setCoupon(coupon);
      const result = await api("POST", "/checkout", {
        shipping_address,
        billing_address: billing_address || shipping_address,
        coupon_code: coupon || null,
        notes: document.getElementById("notes").value.trim() || null,
        payment_method,
        payment_details,
        redeem_points: redeem_points > 0 ? redeem_points : 0,
      });
      if (!result || !result.order) {
        throw new Error(t("checkout.failed"));
      }
      state.pendingPayment = result;
      state.checkoutDraft = null;
      setCartCount(0);
      toast(result.message || t("checkout.created"));
      navigate("payment");
    } catch (e) {
      err.textContent = e.message || t("checkout.failed");
      toast(e.message || t("checkout.failed"), "error");
      btn.disabled = false;
      btn.textContent = t("checkout.continue");
      if (e.authFailed || e.status === 401) navigate("account");
    }
  };
}

async function viewPayment() {
  const root = document.getElementById("app");
  const pending = state.pendingPayment;
  if (!pending?.order) {
    root.innerHTML = `
      <div class="hero"><h1>${t("pay.title")}</h1><p>${t("pay.none")}</p></div>
      <div class="panel"><button class="btn btn-primary" id="to-cart">${t("pay.toCart")}</button></div>`;
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
  const methodLabel = (PAY_METHODS().find((m) => m.id === method) || {}).label || method;

  let formHtml = "";
  if (method === "card") {
    formHtml = `
      <div class="field"><label>${t("pay.cardName")}</label><input id="card-name" value="Test Shopper" /></div>
      <div class="field"><label>${t("pay.cardNum")}</label><input id="card-num" value="4242 4242 4242 4242" maxlength="19" /></div>
      <div class="pay-row">
        <div class="field"><label>${t("pay.expiry")}</label><input id="card-exp" value="12/30" /></div>
        <div class="field"><label>${t("pay.cvc")}</label><input id="card-cvc" value="123" maxlength="4" /></div>
      </div>`;
  } else if (method === "qr" || method === "upi") {
    const qrImg = pending.qr_image_base64
      ? `<div class="qr-box">
          <img class="qr-image" alt="Payment QR" src="data:image/png;base64,${pending.qr_image_base64}" />
          <div class="qr-caption"><strong>${t("pay.qrTitle")}</strong><br/>${t("pay.qrScan")}</div>
          <div class="qr-meta">${t("pay.qrAmount")}: <strong>${money(order.total_amount)}</strong></div>
          <div class="qr-meta">${t("pay.qrVpa")}: <code>${escapeHtml(pending.qr_vpa || "smartcart@upi")}</code></div>
        </div>`
      : `<p class="muted">${t("pay.approveUpi")}</p>`;
    formHtml = `
      ${qrImg}
      <div class="field"><label>${t("pay.upiUsed")}</label><input id="pay-ref" value="${escapeHtml(pending.qr_vpa || "shopper@oksbi")}" /></div>`;
  } else if (method === "netbanking") {
    formHtml = `
      <div class="field"><label>${t("pay.bankLogin")}</label><input id="pay-ref" value="demo_user" /></div>
      <p class="muted">${t("pay.approveNb")}</p>`;
  } else if (method === "wallet") {
    formHtml = `
      <div class="field"><label>${t("pay.walletMobile")}</label><input id="pay-ref" value="9999999999" /></div>
      <p class="muted">${t("pay.approveWallet")}</p>`;
  } else {
    formHtml = `<p class="muted">${t("pay.codConfirmHint")}</p>`;
  }

  const payBtnLabel =
    method === "cod"
      ? t("pay.confirmCod")
      : method === "qr"
        ? t("pay.qrConfirm")
        : t("pay.now", { amount: money(order.total_amount) });

  root.innerHTML = `
    <div class="hero">
      <h1>${t("pay.title")}</h1>
      <p>${escapeHtml(methodLabel)} · ${t("orders.colOrder")} ${escapeHtml(order.order_number)}</p>
    </div>
    <div class="checkout-grid">
      <div class="panel pay-card">
        <div class="pay-brand">${t("pay.brand")} · ${escapeHtml(methodLabel)}</div>
        <p class="muted">${pending.payment_instructions || escapeHtml(pending.message || "")}</p>
        <div class="pay-amount">${money(order.total_amount)}</div>
        ${formHtml}
        <div class="auth-error" id="pay-error"></div>
        <button class="btn btn-primary btn-block" id="pay-success">${payBtnLabel}</button>
        ${
          method !== "cod"
            ? `<button class="btn btn-danger btn-block" id="pay-fail" style="margin-top:0.5rem">${t("pay.fail")}</button>`
            : ""
        }
        <p class="muted" style="margin-top:0.75rem;font-size:0.82rem">${t("pay.sandboxNote")}</p>
      </div>
      <div class="panel">
        <h2>${t("orders.colOrder")} ${escapeHtml(order.order_number)}</h2>
        <div class="summary-line"><span>${t("pay.method")}</span><span>${escapeHtml(methodLabel)}</span></div>
        <div class="summary-line"><span>${t("pay.status")}</span><span>${escapeHtml(order.status)}</span></div>
        <div class="summary-line"><span>${t("pay.payment")}</span><span>${escapeHtml(order.payment_status || "pending")}</span></div>
        <div class="totals">
          <div class="row grand"><span>${t("cart.total")}</span><span>${money(order.total_amount)}</span></div>
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
      await refreshUserProfile();
      if (confirmed.status === "paid") {
        const earned = Number(confirmed.points_earned || 0);
        if (earned > 0) toast(t("loyalty.earned", { pts: earned }));
        else toast(method === "cod" ? t("pay.codOk") : t("pay.success"));
        navigate("confirmation");
        // Auto-generate / download bill after successful payment
        setTimeout(() => downloadBill(confirmed.id, confirmed.order_number), 400);
      } else {
        toast(t("pay.failed"), "error");
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
  const methodLabel = (PAY_METHODS().find((m) => m.id === method) || {}).label || method;
  root.innerHTML = `
    <div class="hero">
      <h1>${t("confirm.title")}</h1>
      <p>${t("confirm.sub")}</p>
    </div>
    <div class="panel confirm-box">
      <div class="confirm-check">✓</div>
      <h2>${t("orders.colOrder")} ${escapeHtml(order.order_number)}</h2>
      <p class="muted">${t("confirm.status")}: <strong>${escapeHtml(order.status)}</strong> ·
        ${t("confirm.payment")}: <strong>${escapeHtml(order.payment_status || "succeeded")}</strong> ·
        ${t("confirm.method")}: <strong>${escapeHtml(methodLabel)}</strong></p>
      <div class="pay-amount" style="margin:1rem 0">${money(order.total_amount)}</div>
      ${
        Number(order.points_earned || 0) > 0
          ? `<p style="font-weight:700;color:var(--teal-deep)">${t("loyalty.earned", {
              pts: order.points_earned,
            })}</p>`
          : ""
      }
      <div class="btn-row" style="justify-content:center;flex-wrap:wrap">
        <button class="btn btn-primary" id="dl-bill">${t("confirm.download")}</button>
        <button class="btn btn-ghost" id="see-orders">${t("confirm.orders")}</button>
        <button class="btn btn-ghost" id="keep-shop">${t("confirm.shop")}</button>
      </div>
    </div>`;
  document.getElementById("dl-bill").onclick = () => downloadBill(order.id, order.order_number);
  document.getElementById("see-orders").onclick = () => navigate("orders");
  document.getElementById("keep-shop").onclick = () => navigate("shop");
  refreshUserProfile();
}

async function viewOrders() {
  const root = document.getElementById("app");
  if (!state.token) {
    navigate("account");
    return;
  }
  const isAdm = isAdmin();
  root.innerHTML = `<div class="hero"><h1>${isAdm ? t("orders.titleAdmin") : t("orders.title")}</h1>
    <p>${isAdm ? t("orders.subAdmin") : t("orders.sub")}</p></div>
    <div class="panel" id="orders">${t("common.loading")}</div>`;
  try {
    const orders = isAdm
      ? await api("GET", "/admin/orders", null, { limit: 50 })
      : await api("GET", "/orders");
    const list = Array.isArray(orders) ? orders : orders.items || [];
    const el = document.getElementById("orders");
    if (!list.length) {
      el.innerHTML = `<p class="muted">${t("orders.empty")}</p><button class="btn btn-primary" id="shop">${t("orders.start")}</button>`;
      document.getElementById("shop").onclick = () => navigate("shop");
      return;
    }
    el.innerHTML = `
      <table class="table">
        <thead><tr><th>${t("orders.colOrder")}</th><th>${t("orders.colStatus")}</th><th>${t("orders.colMethod")}</th><th>${t("orders.colPayment")}</th><th>${t("orders.colTotal")}</th><th>${t("orders.colDate")}</th><th></th></tr></thead>
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
                <button class="btn btn-ghost" data-bill="${o.id}" data-num="${escapeHtml(o.order_number || o.id)}">${t("orders.bill")}</button>
                ${
                  canPay
                    ? `<button class="btn btn-primary" data-pay="${o.id}">${t("orders.pay")}</button>`
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
          message: t("pay.pendingMsg"),
          payment_instructions: t("pay.pendingInstr"),
        };
        navigate("payment");
      })
    );
  } catch (e) {
    toast(e.message, "error");
  }
}

async function loadLoyaltyPanel() {
  const el = document.getElementById("loyalty-panel");
  if (!el) return;
  try {
    const data = await api("GET", "/loyalty/me");
    if (state.user) {
      state.user.loyalty_points = data.balance;
      localStorage.setItem("sc_user", JSON.stringify(state.user));
      renderChrome();
    }
    const role = (state.user?.role || "customer").toLowerCase();
    if (role !== "customer") {
      el.innerHTML = `<div class="muted">${t("loyalty.adminNote")}</div>`;
      return;
    }
    const rules = data.rules || {};
    const dollars = (
      ((rules.min_redeem_points || 100) * (rules.cents_per_point || 1)) /
      100
    ).toFixed(0);
    const history = (data.recent || [])
      .slice(0, 8)
      .map((tx) => {
        const cls = tx.points >= 0 ? "pos" : "neg";
        const sign = tx.points >= 0 ? "+" : "";
        return `<div class="loyalty-tx">
          <span>${escapeHtml(tx.note || tx.tx_type)}</span>
          <span class="${cls}">${sign}${tx.points}</span>
        </div>`;
      })
      .join("");
    el.innerHTML = `
      <div class="muted">${t("loyalty.title")}</div>
      <div class="loyalty-balance">${data.balance} <small>${t("loyalty.pts")}</small></div>
      <div class="loyalty-meta">
        <span>${t("loyalty.earnedLife")}: <strong>${data.lifetime_earned}</strong></span>
        <span>${t("loyalty.redeemedLife")}: <strong>${data.lifetime_redeemed}</strong></span>
      </div>
      <p class="muted" style="margin-top:0.55rem;font-size:0.85rem">${t("loyalty.rules", {
        earn: rules.points_per_dollar || 1,
        min: rules.min_redeem_points || 100,
        dollars,
        bonus: rules.signup_bonus || 50,
      })}</p>
      <h3 style="margin-top:0.85rem;font-size:1rem">${t("loyalty.history")}</h3>
      ${history || `<p class="muted">${t("loyalty.empty")}</p>`}
    `;
  } catch (e) {
    el.innerHTML = `<p class="muted">${escapeHtml(e.message)}</p>`;
  }
}

function viewAccount() {
  const root = document.getElementById("app");

  if (state.user) {
    const name = state.user.name || state.user.full_name || "User";
    const role = (state.user.role || "customer").toLowerCase();
    root.innerHTML = `
      <div class="hero">
        <h1>${t("account.mine")}</h1>
        <p>${t("account.signedAs", { role: tRole(role) })}</p>
      </div>
      <div class="panel profile-card">
        <h2>${escapeHtml(name)}</h2>
        <p class="muted">${t("account.userId")} · ${escapeHtml(state.user.email || "")}</p>
        <span class="role-pill ${role === "admin" ? "admin" : "customer"}">${escapeHtml(tRole(role))}</span>
        <div id="loyalty-panel" class="loyalty-card"><div class="muted">${t("common.loading")}</div></div>
        <div class="btn-row" style="margin-top:1rem">
          <button class="btn btn-primary" id="go-shop">${t("account.continue")}</button>
          ${isAdmin() ? `<button class="btn btn-ghost" id="go-admin">${t("account.adminDash")}</button>` : ""}
          <button class="btn btn-danger" id="do-logout">${t("user.logout")}</button>
        </div>
      </div>`;
    document.getElementById("go-shop").onclick = () => navigate("shop");
    const goAdmin = document.getElementById("go-admin");
    if (goAdmin) goAdmin.onclick = () => navigate("admin");
    document.getElementById("do-logout").onclick = () => {
      clearAuth();
      toast(t("account.loggedOut"));
      viewAccount();
      renderChrome();
    };
    loadLoyaltyPanel();
    return;
  }

  root.innerHTML = `
    <div class="hero">
      <h1>${t("account.title")}</h1>
      <p>${t("account.sub")}</p>
    </div>

    <div class="demo-box">
      <strong>${t("account.demo")}</strong><br />
      ${t("account.userId")}: <code>admin@smartcart.com</code> &nbsp;·&nbsp;
      ${t("account.password")}: <code>Admin@12345</code>
      <div class="btn-row" style="margin-top:0.65rem">
        <button class="btn btn-ghost" type="button" id="fill-admin">${t("account.useAdmin")}</button>
      </div>
    </div>

    <div class="auth-tabs">
      <button class="auth-tab active" type="button" data-tab="login">${t("account.tabLogin")}</button>
      <button class="auth-tab" type="button" data-tab="register">${t("account.tabReg")}</button>
    </div>

    <div class="panel" id="panel-login">
      <h2>${t("account.signIn")}</h2>
      <p class="muted" style="margin-bottom:0.85rem">${t("account.signInHint")}</p>
      <div class="field">
        <label>${t("account.email")}</label>
        <input id="login-email" type="email" autocomplete="username" placeholder="you@example.com" />
      </div>
      <div class="field">
        <label>${t("account.password")}</label>
        <input id="login-pass" type="password" autocomplete="current-password" placeholder="••••••••" />
      </div>
      <div class="auth-error" id="login-error"></div>
      <button class="btn btn-primary btn-block" id="btn-login">${t("account.loginBtn")}</button>
    </div>

    <div class="panel hidden" id="panel-register">
      <h2>${t("account.createTitle")}</h2>
      <p class="muted" style="margin-bottom:0.85rem">${t("account.createHint")}</p>
      <div class="field">
        <label>${t("account.fullName")}</label>
        <input id="reg-name" autocomplete="name" placeholder="Jane Shopper" />
      </div>
      <div class="field">
        <label>${t("account.email")}</label>
        <input id="reg-email" type="email" autocomplete="username" placeholder="jane@example.com" />
      </div>
      <div class="field">
        <label>${t("account.phone")}</label>
        <input id="reg-phone" type="tel" placeholder="+1 555 0100" />
      </div>
      <div class="field">
        <label>${t("account.password")}</label>
        <input id="reg-pass" type="password" autocomplete="new-password" placeholder="Min. 8 characters" />
      </div>
      <div class="field">
        <label>${t("account.confirmPw")}</label>
        <input id="reg-pass2" type="password" autocomplete="new-password" />
      </div>
      <div class="auth-error" id="reg-error"></div>
      <button class="btn btn-primary btn-block" id="btn-reg">${t("account.createBtn")}</button>
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
    toast(t("account.filled"));
  };

  document.getElementById("btn-login").onclick = async () => {
    const err = document.getElementById("login-error");
    err.textContent = "";
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-pass").value;
    if (!email || !password) {
      err.textContent = t("account.needCreds");
      return;
    }
    try {
      const data = await api("POST", "/auth/login", { email, password });
      saveAuth(data);
      const role = (data.user?.role || "customer").toLowerCase();
      toast(role === "admin" ? t("account.welcomeAdmin") : t("account.welcomeBack"));
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
      err.textContent = t("account.needName");
      return;
    }
    if (!email) {
      err.textContent = t("account.needEmail");
      return;
    }
    if (password.length < 8) {
      err.textContent = t("account.pwLen");
      return;
    }
    if (password !== password2) {
      err.textContent = t("account.pwMatch");
      return;
    }

    try {
      const payload = { full_name, email, password };
      if (phone) payload.phone = phone;
      const data = await api("POST", "/auth/register", payload);
      saveAuth(data);
      const bonus = Number(data.user?.loyalty_points || 0);
      if (bonus > 0) toast(t("loyalty.signup", { pts: bonus }));
      else toast(t("account.created"));
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
    toast(t("admin.only"), "error");
    navigate("shop");
    return;
  }
  const root = document.getElementById("app");
  root.innerHTML = `
    <div class="hero"><h1>${t("admin.title")}</h1><p>${t("admin.sub")}</p></div>
    <div class="btn-row" style="margin-bottom:1rem">
      <button class="btn btn-primary" id="go-catalog">${t("admin.manage")}</button>
      <button class="btn btn-ghost" id="go-shop-admin">${t("admin.viewShop")}</button>
    </div>
    <div id="kpis" class="kpi-row"><div class="muted">${t("common.loading")}</div></div>
    <div class="section-title">${t("admin.top")}</div>
    <div class="panel" id="top"></div>
    <div class="section-title">${t("admin.low")}</div>
    <div class="panel" id="low"></div>
    <div class="section-title">${t("admin.coupons")}</div>
    <div class="panel" id="coupons"></div>
    <div class="section-title">${t("admin.inventory")}</div>
    <div class="panel" id="inv"></div>`;
  document.getElementById("go-catalog").onclick = () => navigate("catalog");
  document.getElementById("go-shop-admin").onclick = () => navigate("shop");
  try {
    const dash = await api("GET", "/analytics/dashboard");
    state.dash = dash;
    const k = dash.kpis || {};
    document.getElementById("kpis").innerHTML = [
      [t("admin.todayRev"), money(k.today_revenue), ""],
      [t("admin.monthRev"), money(k.monthly_revenue), "sky"],
      [t("admin.totalOrders"), k.total_orders ?? 0, "coral"],
      [t("admin.users"), k.users ?? 0, "amber"],
      [t("admin.pending"), k.pending_orders ?? 0, "amber"],
      [t("admin.cancelled"), k.cancelled_orders ?? 0, "coral"],
      [t("admin.low"), k.low_stock_count ?? 0, "lime"],
      [t("admin.activeCoupons"), k.active_coupons ?? 0, "sky"],
    ]
      .map(
        ([label, value, tone]) =>
          `<div class="kpi ${tone}"><div class="label">${label}</div><div class="value">${value}</div></div>`
      )
      .join("");

    const table = (rows, cols) => {
      if (!rows || !rows.length) return `<p class="muted">${t("admin.nothing")}</p>`;
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
        ${t("admin.products")}: <strong>${inv.total_products ?? 0}</strong> ·
        ${t("admin.lowStock")}: <strong>${inv.low_stock_count ?? 0}</strong> ·
        ${t("admin.outStock")}: <strong>${inv.out_of_stock_count ?? 0}</strong>
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
    toast(t("admin.only"), "error");
    navigate("shop");
    return;
  }
  const root = document.getElementById("app");
  root.innerHTML = `
    <div class="hero">
      <h1>${t("catalog.title")}</h1>
      <p>${t("catalog.sub")}</p>
    </div>
    <div class="checkout-grid">
      <div class="panel">
        <h2>${t("catalog.addProduct")}</h2>
        <div class="field">
          <label>${t("catalog.name")}</label>
          <input id="p-name" placeholder="Galaxy Phone Case" />
        </div>
        <div class="field">
          <label>${t("catalog.sku")}</label>
          <input id="p-sku" placeholder="MB-CASE-001" />
        </div>
        <div class="field">
          <label>${t("catalog.desc")}</label>
          <textarea id="p-desc" placeholder="Product details for shoppers…"></textarea>
        </div>
        <div class="pay-row">
          <div class="field">
            <label>${t("catalog.price")}</label>
            <input id="p-price" type="number" min="0.01" step="0.01" placeholder="49.99" />
          </div>
          <div class="field">
            <label>${t("catalog.stock")}</label>
            <input id="p-stock" type="number" min="0" step="1" value="25" />
          </div>
        </div>
        <div class="field">
          <label>${t("catalog.category")}</label>
          <select id="p-cat"></select>
        </div>
        <div class="field">
          <label>${t("catalog.image")}</label>
          <input id="p-image" placeholder="https://…" />
          <div class="preset-row" id="img-presets"></div>
          <img id="p-preview" class="img-preview hidden" alt="Preview" />
        </div>
        <label class="check-row">
          <input type="checkbox" id="p-featured" /> ${t("catalog.featured")}
        </label>
        <div class="auth-error" id="p-error"></div>
        <button class="btn btn-primary btn-block" id="p-save">${t("catalog.save")}</button>
      </div>

      <div>
        <div class="panel">
          <h2>${t("catalog.addCat")}</h2>
          <div class="field">
            <label>${t("catalog.catName")}</label>
            <input id="c-name" placeholder="${t("catalog.catPh")}" />
          </div>
          <div class="field">
            <label>${t("catalog.catDesc")}</label>
            <input id="c-desc" placeholder="Short description" />
          </div>
          <div class="auth-error" id="c-error"></div>
          <button class="btn btn-ghost btn-block" id="c-save">${t("catalog.createCat")}</button>
          <div id="cat-list" class="muted" style="margin-top:0.85rem"></div>
        </div>
        <div class="panel" style="margin-top:1rem">
          <h2>${t("catalog.shopCatalog")}</h2>
          <div id="admin-products"><div class="muted">${t("catalog.loading")}</div></div>
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
    sel.innerHTML = `<option value="">${t("catalog.selectCat")}</option>` +
      cats.map((c) => `<option value="${c.id}">${escapeHtml(tCat(c.name))}</option>`).join("");
    document.getElementById("cat-list").innerHTML =
      cats.map((c) => `<span class="chip">${escapeHtml(tCat(c.name))}</span>`).join(" ") ||
      t("catalog.noCats");
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
      box.innerHTML = `<p class="muted">${t("catalog.none")}</p>`;
      return;
    }
    box.innerHTML = items
      .map(
        (p) => `
      <div class="admin-product-row">
        <img src="${escapeHtml(p.image_url || p.image || "")}" alt="" />
        <div>
          <strong>${escapeHtml(p.name)}</strong>
          <div class="muted">${escapeHtml(tCat((p.category && p.category.name) || "") || t("catalog.uncat"))} · ${money(p.price)} · ${t("catalog.stock")} ${p.stock_quantity ?? p.stock ?? 0}</div>
        </div>
        <div class="btn-row">
          <button class="btn btn-ghost" data-view="${p.id}">${t("catalog.view")}</button>
          <button class="btn btn-danger" data-del="${p.id}">${t("catalog.delete")}</button>
        </div>
      </div>`
      )
      .join("");
    box.querySelectorAll("[data-view]").forEach((b) =>
      b.addEventListener("click", () => navigate("product", { productId: Number(b.dataset.view) }))
    );
    box.querySelectorAll("[data-del]").forEach((b) =>
      b.addEventListener("click", async () => {
        if (!confirm(t("catalog.confirmDel"))) return;
        try {
          await api("DELETE", `/products/${b.dataset.del}`);
          toast(t("catalog.deleted"));
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
      err.textContent = t("catalog.needCatName");
      return;
    }
    try {
      await api("POST", "/categories", { name, description: description || null, is_active: true });
      toast(t("catalog.catCreated", { name }));
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
      err.textContent = t("catalog.needName");
      return;
    }
    if (sku.length < 2) {
      err.textContent = t("catalog.needSku");
      return;
    }
    if (!(price > 0)) {
      err.textContent = t("catalog.needPrice");
      return;
    }
    if (!category_id) {
      err.textContent = t("catalog.needCat");
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
      toast(t("catalog.added", { name: created.name }));
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
    await Promise.all([loadCategories(), loadProducts()]);
  } catch (e) {
    toast(e.message, "error");
  }
}

function boot() {
  try {
    document.documentElement.lang = getLang() === "hi" ? "hi" : "en";
    document.title = t("meta.title");
    if (getLang() === "hi" && typeof ensureHiFont === "function") ensureHiFont();
    document.querySelectorAll("[data-lang-btn]").forEach((btn) => {
      btn.addEventListener("click", () => setLang(btn.dataset.langBtn));
    });
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
    applyStaticI18n();
    renderChrome();
    // Paint shop immediately; validate session + cart in background
    navigate("shop");
    if (state.token) {
      ensureAuthSession()
        .then(() => refreshCartSummary())
        .catch((err) => console.error(err));
    }
  } catch (err) {
    const root = document.getElementById("app");
    if (root) {
      root.innerHTML = `<div class="panel"><p class="muted">${t("ui.fail")}: ${escapeHtml(String(err))}</p></div>`;
    }
    console.error(err);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
