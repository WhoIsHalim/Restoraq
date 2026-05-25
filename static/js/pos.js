const POS_DB_NAME = "restoraq-pos";
const POS_STORE = "pending_orders";

function generateUuid() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  return `fallback-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function openPosDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(POS_DB_NAME, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(POS_STORE)) {
        db.createObjectStore(POS_STORE, { keyPath: "client_order_uuid" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function savePendingOrder(order) {
  const db = await openPosDb();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(POS_STORE, "readwrite");
    tx.objectStore(POS_STORE).put(order);
    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

async function getPendingOrders() {
  const db = await openPosDb();
  const rows = await new Promise((resolve, reject) => {
    const tx = db.transaction(POS_STORE, "readonly");
    const req = tx.objectStore(POS_STORE).getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
  db.close();
  return rows;
}

async function clearPendingOrder(clientOrderUuid) {
  const db = await openPosDb();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(POS_STORE, "readwrite");
    tx.objectStore(POS_STORE).delete(clientOrderUuid);
    tx.oncomplete = () => resolve(true);
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

function resolveCsrfToken() {
  if (typeof window.getCsrfToken === "function" && window.getCsrfToken !== resolveCsrfToken) {
    const token = window.getCsrfToken();
    if (token) return token;
  }
  const name = "csrftoken";
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return "";
}

function round2(value) {
  return Math.round((Number(value) + Number.EPSILON) * 100) / 100;
}

function calculateLocalTotals(items) {
  let subtotal = 0;
  let tax = 0;
  let total = 0;
  for (const item of items || []) {
    const qty = Number(item.quantity || 0);
    const price = Number(item.price || 0);
    const rate = Number(item.tax_rate || 0);
    const lineAmount = price * qty;

    if (item.is_tax_inclusive) {
      const divisor = 1 + rate / 100;
      const lineSubtotal = divisor > 0 ? lineAmount / divisor : lineAmount;
      const lineTax = lineAmount - lineSubtotal;
      subtotal += lineSubtotal;
      tax += lineTax;
      total += lineAmount;
    } else {
      const lineTax = lineAmount * (rate / 100);
      subtotal += lineAmount;
      tax += lineTax;
      total += lineAmount + lineTax;
    }
  }
  return {
    subtotal: round2(subtotal).toFixed(2),
    tax: round2(tax).toFixed(2),
    total: round2(total).toFixed(2),
  };
}

function cloneForStorage(value) {
  if (typeof structuredClone === "function") {
    try {
      return structuredClone(value);
    } catch (_) {}
  }
  return JSON.parse(JSON.stringify(value));
}

async function readApiError(response, language, fallbackMessage) {
  const sessionExpired = language === "ar"
    ? "انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى."
    : "Your session has expired. Please login again.";

  if (response.redirected || (response.url && response.url.includes("/accounts/login/"))) {
    return sessionExpired;
  }

  const contentType = (response.headers.get("content-type") || "").toLowerCase();
  const raw = await response.text();
  if (!raw) return fallbackMessage;

  if (contentType.includes("application/json")) {
    try {
      const payload = JSON.parse(raw);
      if (payload.error === "authentication_required") return sessionExpired;
      if (typeof payload.error === "string" && payload.error.trim()) return payload.error;
      if (typeof payload.detail === "string" && payload.detail.trim()) return payload.detail;
    } catch (_) {}
  }

  if (/<html|<!doctype/i.test(raw)) return fallbackMessage;
  return raw.length > 300 ? `${raw.slice(0, 300)}...` : raw;
}

async function pushPendingOrdersToServer(language) {
  const pending = await getPendingOrders();
  if (!pending.length) return;

  const response = await fetch("/pos/api/sync-orders/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": resolveCsrfToken(),
    },
    body: JSON.stringify({ orders: pending }),
  });
  if (!response.ok) {
    const fallback = language === "ar" ? "تعذر مزامنة الطلبات المعلقة." : "Failed to sync pending orders.";
    throw new Error(await readApiError(response, language, fallback));
  }

  const data = await response.json();
  const syncedRows = data.synced || [];
  for (const synced of syncedRows) {
    if (synced.client_order_uuid) {
      await clearPendingOrder(synced.client_order_uuid);
    }
  }
}

function createOrderState(activeBranchId) {
  return {
    id: generateUuid(),
    client_order_uuid: generateUuid(),
    branch_id: activeBranchId,
    cart: [],
    notes: "",
    preview: { subtotal: "0.00", tax: "0.00", total: "0.00" },
    checkoutReady: false,
    status: "draft",
    paymentMethod: null,
    paymentProcessing: false,
    receipts: { customer: false, kitchen: false, delivery: false },
    serverId: null,
    orderType: "dine_in",
    customer: {
      id: null,
      name: "",
      phone: "",
      address: "",
      matches: [],
      lookupBusy: false,
    },
  };
}

function posTerminal(defaultLanguage = "ar") {
  return {
    language: defaultLanguage,
    online: navigator.onLine,
    categories: [],
    products: [],
    branches: [],
    branchLocked: false,
    activeBranchId: null,
    activeCategory: null,
    orders: [],
    activeOrderId: null,
    lastError: null,
    paymentMethods: [
      {
        id: "vodafone_cash",
        apiMethod: "wallet",
        reference: "vodafone_cash",
        label: { ar: "فودافون كاش", en: "Vodafone Cash" },
      },
      {
        id: "entspay",
        apiMethod: "wallet",
        reference: "entspay",
        label: { ar: "انتسباي", en: "Entspay" },
      },
      {
        id: "cash",
        apiMethod: "cash",
        reference: "cash",
        label: { ar: "نقدي", en: "Cash" },
      },
    ],

    get filteredProducts() {
      if (!this.activeCategory) return this.products;
      return this.products.filter((p) => p.category_id === this.activeCategory);
    },

    get activeOrder() {
      return this.orders.find((order) => order.id === this.activeOrderId) || null;
    },

    async init() {
      this.online = navigator.onLine;
      this.createNewOrder();

      window.addEventListener("online", async () => {
        this.online = true;
        try {
          await pushPendingOrdersToServer(this.language);
        } catch (err) {
          this.lastError = err.message || (this.language === "ar" ? "تعذر مزامنة الطلبات المعلقة." : "Failed to sync pending orders.");
        }
      });

      window.addEventListener("offline", () => {
        this.online = false;
      });

      try {
        await this.loadMenu();
      } catch (err) {
        this.lastError = err.message || (this.language === "ar" ? "تعذر تحميل قائمة المنيو." : "Failed to load menu catalog.");
      }
    },

    async loadMenu(branchId = null) {
      this.lastError = null;
      const qs = branchId ? `?branch_id=${encodeURIComponent(branchId)}` : "";
      const res = await fetch(`/pos/api/menu/${qs}`);
      if (!res.ok) {
        const fallback = this.language === "ar" ? "تعذر تحميل قائمة المنيو." : "Failed to load menu catalog.";
        throw new Error(await readApiError(res, this.language, fallback));
      }
      const data = await res.json();
      this.categories = data.categories || [];
      this.products = data.products || [];
      this.branches = (data.branches || []).map((b) => ({ ...b, id: String(b.id) }));
      this.branchLocked = Boolean(data.branch_locked);
      this.activeBranchId = data.active_branch_id ? String(data.active_branch_id) : this.activeBranchId;
      if (this.categories.length && !this.categories.some((c) => c.id === this.activeCategory)) {
        this.activeCategory = this.categories[0].id;
      }
      for (const order of this.orders) {
        if (!order.branch_id) order.branch_id = this.activeBranchId;
      }
    },

    async changeBranch(branchId) {
      if (this.branchLocked) return;
      this.activeBranchId = branchId || null;
      await this.loadMenu(this.activeBranchId);
    },

    createNewOrder() {
      const newOrder = createOrderState(this.activeBranchId);
      this.orders.push(newOrder);
      this.activeOrderId = newOrder.id;
      this.lastError = null;
    },

    selectOrder(orderId) {
      this.activeOrderId = orderId;
      this.lastError = null;
    },

    setOrderType(order, type) {
      if (!order) return;
      order.orderType = type;
      if (type !== "delivery") {
        order.customer = {
          id: null,
          name: "",
          phone: "",
          address: "",
          matches: [],
          lookupBusy: false,
        };
      }
    },

    addProduct(product) {
      if (!this.activeOrder) this.createNewOrder();
      const order = this.activeOrder;
      if (!order) return;
      const existing = order.cart.find((x) => x.product_id === product.id);
      if (existing) {
        existing.quantity += 1;
      } else {
        order.cart.push({
          product_id: product.id,
          name: product.name,
          price: product.price,
          tax_rate: Number(product.tax_rate || 0),
          is_tax_inclusive: Boolean(product.is_tax_inclusive),
          quantity: 1,
        });
      }
      if (!order.branch_id) order.branch_id = this.activeBranchId;
      order.checkoutReady = false;
      this.recalculate(order);
    },

    increment(item) {
      item.quantity += 1;
      const order = this.activeOrder;
      if (!order) return;
      order.checkoutReady = false;
      this.recalculate(order);
    },

    decrement(item) {
      item.quantity -= 1;
      const order = this.activeOrder;
      if (!order) return;
      if (item.quantity <= 0) {
        order.cart = order.cart.filter((x) => x.product_id !== item.product_id);
      }
      order.checkoutReady = false;
      this.recalculate(order);
    },

    async lookupCustomerByPhone(order) {
      if (!order || order.orderType !== "delivery") return;
      const phone = (order.customer.phone || "").trim();
      if (phone.length < 3) {
        order.customer.matches = [];
        return;
      }
      order.customer.lookupBusy = true;
      try {
        const params = new URLSearchParams({ phone, branch_id: order.branch_id || this.activeBranchId || "" });
        const res = await fetch(`/pos/api/customers/?${params.toString()}`);
        if (!res.ok) {
          const fallback = this.language === "ar" ? "تعذر تحميل بيانات العملاء." : "Failed to load customers.";
          this.lastError = await readApiError(res, this.language, fallback);
          return;
        }
        const data = await res.json();
        order.customer.matches = data.results || [];
      } catch (_) {
        this.lastError = this.language === "ar" ? "تعذر تحميل بيانات العملاء." : "Failed to load customers.";
      } finally {
        order.customer.lookupBusy = false;
      }
    },

    selectCustomerMatch(order, row) {
      if (!order || !row) return;
      order.customer.id = row.id;
      order.customer.name = row.name || "";
      order.customer.phone = row.phone || "";
      order.customer.address = row.address || "";
      order.customer.matches = [];
    },

    openPayment() {
      const order = this.activeOrder;
      if (!order || !order.cart.length) return;
      order.checkoutReady = true;
      order.paymentMethod = null;
      order.paymentProcessing = false;
      this.lastError = null;
    },

    selectPayment(methodId) {
      const order = this.activeOrder;
      if (!order) return;
      order.paymentMethod = methodId;
      if (order.checkoutReady && !order.paymentProcessing) {
        this.confirmPayment(methodId);
      }
    },

    validateOrderBeforePayment(order) {
      if (!order) return false;
      if (order.orderType !== "delivery") return true;
      const name = (order.customer.name || "").trim();
      const phone = (order.customer.phone || "").trim();
      const address = (order.customer.address || "").trim();
      if (!name || !phone || !address) {
        this.lastError = this.language === "ar"
          ? "يرجى إدخال بيانات عميل الدليفري كاملة (الاسم، الهاتف، العنوان)."
          : "Please provide full delivery customer details (name, phone, address).";
        return false;
      }
      return true;
    },

    async recalculate(order) {
      if (!order || !order.cart.length) {
        if (order) order.preview = { subtotal: "0.00", tax: "0.00", total: "0.00" };
        return;
      }

      const fallbackMessage = this.language === "ar" ? "تعذر حساب الإجمالي." : "Failed to calculate totals.";
      try {
        const res = await fetch("/pos/api/order/preview/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": resolveCsrfToken(),
          },
          body: JSON.stringify({ items: order.cart, branch_id: order.branch_id || this.activeBranchId }),
        });

        if (!res.ok) {
          order.preview = calculateLocalTotals(order.cart);
          this.lastError = await readApiError(res, this.language, fallbackMessage);
          return;
        }

        const contentType = (res.headers.get("content-type") || "").toLowerCase();
        if (!contentType.includes("application/json")) {
          order.preview = calculateLocalTotals(order.cart);
          this.lastError = await readApiError(res, this.language, fallbackMessage);
          return;
        }

        order.preview = await res.json();
        this.lastError = null;
      } catch (_) {
        order.preview = calculateLocalTotals(order.cart);
        this.lastError = this.language === "ar"
          ? "تعذر الاتصال بالخادم أثناء حساب الإجمالي. تم الحساب محلياً."
          : "Connection error while calculating totals. Local totals are applied.";
      }
    },

    async confirmPayment(methodId) {
      const order = this.activeOrder;
      if (!order || !order.cart.length || !order.checkoutReady) return;
      const selectedMethod = methodId || order.paymentMethod;
      if (!selectedMethod) {
        this.lastError = this.language === "ar" ? "يرجى اختيار وسيلة الدفع أولاً." : "Please select a payment method first.";
        return;
      }
      const branchId = order.branch_id || this.activeBranchId;
      if (!branchId) {
        this.lastError = this.language === "ar" ? "يرجى اختيار الفرع أولاً." : "Please select a branch first.";
        return;
      }
      if (!this.validateOrderBeforePayment(order)) return;
      this.lastError = null;

      const methodDef = this.paymentMethods.find((m) => m.id === selectedMethod);
      if (!methodDef) return;
      order.paymentProcessing = true;
      const onlineNow = navigator.onLine;
      this.online = onlineNow;

      const payload = {
        client_order_uuid: order.client_order_uuid,
        created_at: new Date().toISOString(),
        branch_id: branchId,
        order_type: order.orderType,
        notes: (order.notes || "").trim(),
        customer: order.orderType === "delivery" ? {
          id: order.customer.id,
          name: (order.customer.name || "").trim(),
          phone: (order.customer.phone || "").trim(),
          address: (order.customer.address || "").trim(),
        } : null,
        items: order.cart.map((x) => ({ product_id: x.product_id, quantity: x.quantity })),
        payments: [
          {
            method: methodDef.apiMethod,
            amount: order.preview.total,
            reference: methodDef.reference,
          },
        ],
        totals: order.preview,
      };

      const pendingPayload = cloneForStorage(payload);

      try {
        const fallbackMessage = this.language === "ar" ? "تعذر إنشاء الطلب." : "Order creation failed.";
        const createUrl = `${window.location.origin}/orders/api/create/`;
        const response = await fetch(createUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": resolveCsrfToken(),
          },
          body: JSON.stringify(payload),
        });
        if (response.ok) {
          const data = await response.json();
          order.status = "completed";
          order.serverId = data.id;
          order.pending_sync = false;
          order.checkoutReady = false;
        } else {
          this.lastError = await readApiError(response, this.language, fallbackMessage);
          order.paymentProcessing = false;
          return;
        }
      } catch (err) {
        const errMsg = err && err.message ? err.message : String(err || "");
        if (errMsg) {
          this.lastError = this.language === "ar"
            ? `تعذر إرسال الطلب. ${errMsg}`
            : `Failed to send order. ${errMsg}`;
        }
        if (typeof console !== "undefined" && console.error) {
          console.error("Order create failed", err);
        }
        await savePendingOrder(pendingPayload);
        order.status = "pending_sync";
        order.pending_sync = true;
        order.checkoutReady = false;
      }

      order.paymentMethod = selectedMethod;
      order.receipts = { customer: false, kitchen: false, delivery: false };
      order.paymentProcessing = false;
    },

    async printReceipt(order, template) {
      if (!order || !order.serverId) return;
      const response = await fetch("/printing/api/jobs/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": resolveCsrfToken(),
        },
        body: JSON.stringify({ order_id: order.serverId, template_type: template }),
      });
      if (!response.ok) {
        const fallback = this.language === "ar" ? "تعذر إرسال أمر الطباعة." : "Failed to create print job.";
        this.lastError = await readApiError(response, this.language, fallback);
        return;
      }
      order.receipts[template] = true;
    },
  };
}

window.posTerminal = posTerminal;
