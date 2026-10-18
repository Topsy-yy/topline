/**
 * TopLine Frontend Application Script
 * Connects the landing page, dynamic database job listings, category/country filtering,
 * interactive job details modal, worker registration, OTP verification, KSh 1,000 M-Pesa
 * activation, application submission, document upload, and worker portal.
 */

let currentJobs = [];
let currentCategory = "All";
let selectedJobForApply = null;

async function initTopLineApp() {
  await loadCategories();
  await loadJobs();
  checkAuthSession();
  setupRegistrationForm();
  setupSignInForm();
}

async function loadCategories() {
  const chipsEl = document.getElementById("chips");
  if (!chipsEl) return;
  try {
    const categories = await window.apiClient.getCategories();
    const allCategories = ["All", ...categories];
    chipsEl.innerHTML = allCategories.map(c => `
      <button class="chip ${c === currentCategory ? 'on' : ''}" data-c="${c}">
        ${c}
      </button>
    `).join("");

    chipsEl.querySelectorAll(".chip").forEach(btn => {
      btn.addEventListener("click", () => {
        currentCategory = btn.dataset.c;
        chipsEl.querySelectorAll(".chip").forEach(b => b.classList.remove("on"));
        btn.classList.add("on");
        renderJobs();
      });
    });
  } catch (err) {
    console.error("Failed to load categories:", err);
  }
}

async function loadJobs() {
  const listEl = document.getElementById("list");
  if (!listEl) return;
  listEl.innerHTML = `<div style="text-align:center;padding:24px;color:var(--mut);">Loading verified jobs from database...</div>`;

  try {
    currentJobs = await window.apiClient.getJobs();
    renderJobs();
  } catch (err) {
    listEl.innerHTML = `
      <div style="background:#fee2e2;color:#b91c1c;padding:16px;border-radius:10px;text-align:center;">
        Failed to load jobs from server: ${err.message}. Please verify the backend is running.
      </div>
    `;
  }
}

function renderJobs() {
  const listEl = document.getElementById("list");
  if (!listEl) return;

  const filtered = currentJobs.filter(j => currentCategory === "All" || j.category.toLowerCase() === currentCategory.toLowerCase());

  if (filtered.length === 0) {
    listEl.innerHTML = `<div style="text-align:center;padding:32px;color:var(--mut);">No jobs found in this category.</div>`;
    return;
  }

  listEl.innerHTML = filtered.map(j => {
    const verifiedBadge = j.is_verified 
      ? `<span class="ok" title="Verified against commercial registry and contractor licence">✓ Verified</span>` 
      : `<span style="background:#f1f5f9;color:#64748b;border-radius:99px;padding:3px 10px;font-size:12px;font-weight:600;">Unverified</span>`;

    const salaryFormatted = `${j.salary_currency} ${j.salary_min.toLocaleString()} - ${j.salary_max.toLocaleString()}/${j.salary_period}`;

    return `
      <div class="card job" style="transition:box-shadow .2s;cursor:pointer;" onclick="openJobModal('${j.id}')">
        <div style="flex:1;">
          <b>${escapeHtml(j.title)}</b>
          <div class="meta">${escapeHtml(j.city)}, ${escapeHtml(j.country)} · ${escapeHtml(j.category)} · <span class="lock">${salaryFormatted}</span></div>
          ${j.employer_name ? `<div style="font-size:12px;color:var(--mut);margin-top:4px;">Employer: ${escapeHtml(j.employer_name)}</div>` : ''}
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
          ${verifiedBadge}
          <button class="btn s" onclick="event.stopPropagation();openJobModal('${j.id}')">View Details &amp; Apply</button>
        </div>
      </div>
    `;
  }).join("");
}

function openJobModal(jobId) {
  const job = currentJobs.find(j => j.id === jobId);
  if (!job) return;
  selectedJobForApply = job;

  let modal = document.getElementById("job-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "job-modal";
    modal.style.cssText = `
      position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);
      display:flex;align-items:center;justify-content:center;z-index:9999;padding:16px;box-sizing:border-box;
    `;
    document.body.appendChild(modal);
  }

  const verifiedDetails = job.is_verified 
    ? `<div style="background:#e6f7ec;color:#14703a;padding:10px 14px;border-radius:8px;font-size:13px;margin:12px 0;">
        <b>✓ Verified Job Opportunity</b><br>
        Verified by TopLine Administrator via official contractor registries.
       </div>`
    : `<div style="background:#fef3c7;color:#92400e;padding:10px 14px;border-radius:8px;font-size:13px;margin:12px 0;">
        Verification pending administrative review.
       </div>`;

  const salaryDisplay = `${job.salary_currency} ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()} per ${job.salary_period}`;

  modal.innerHTML = `
    <div style="background:var(--card);max-width:540px;width:100%;border-radius:16px;padding:26px;box-shadow:0 20px 25px -5px rgba(0,0,0,0.2);max-height:90vh;overflow-y:auto;position:relative;">
      <button onclick="closeJobModal()" style="position:absolute;top:16px;right:16px;background:none;border:none;font-size:22px;cursor:pointer;color:var(--mut);">&times;</button>
      <h2 style="margin:0 0 4px;font-size:24px;">${escapeHtml(job.title)}</h2>
      <div class="meta" style="margin-bottom:12px;">${escapeHtml(job.city)}, ${escapeHtml(job.country)} · ${escapeHtml(job.category)}</div>
      
      ${verifiedDetails}

      <div style="margin:14px 0;background:var(--bg2);padding:12px;border-radius:10px;">
        <span style="font-size:13px;color:var(--mut);display:block;">Salary Offer</span>
        <b style="font-size:18px;color:var(--navy);">${salaryDisplay}</b>
      </div>

      <div style="margin:16px 0;">
        <h4 style="margin:0 0 6px;">Job Description</h4>
        <p style="margin:0;font-size:14px;color:var(--tx);line-height:1.5;">${escapeHtml(job.description)}</p>
      </div>

      <div style="margin:16px 0;">
        <h4 style="margin:0 0 6px;">Job Requirements</h4>
        <p style="margin:0;font-size:14px;color:var(--tx);line-height:1.5;">${escapeHtml(job.requirements)}</p>
      </div>

      <div id="modal-app-section" style="margin-top:20px;border-top:1px solid var(--bd);padding-top:16px;">
        <button class="btn" style="width:100%;text-align:center;" onclick="startApplicationFlow('${job.id}')">Apply For This Position</button>
      </div>
    </div>
  `;
  modal.style.display = "flex";
}

function closeJobModal() {
  const modal = document.getElementById("job-modal");
  if (modal) modal.style.display = "none";
}

async function startApplicationFlow(jobId) {
  const token = window.apiClient.getToken();
  if (!token) {
    alert("Please register or log in first to apply for jobs.");
    closeJobModal();
    window.location.hash = "#join";
    return;
  }

  const appSection = document.getElementById("modal-app-section");
  if (!appSection) return;

  try {
    const access = await window.apiClient.getMyAccess();
    if (!access.is_activated) {
      appSection.innerHTML = `
        <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:16px;text-align:left;">
          <h4 style="margin:0 0 6px;color:#92400e;">Platform Activation Required</h4>
          <p style="margin:0 0 12px;font-size:14px;color:#b45309;">
            To submit your verified application, CV, and certificates directly to Gulf contractors, a one-time platform access fee of <b>KSh 1,000</b> is required.
          </p>
          <button class="btn" style="width:100%;" onclick="triggerMpesaPaymentModal()">Unlock Access via M-Pesa (KSh 1,000)</button>
        </div>
      `;
      return;
    }

    // Activated - show application form with document upload
    appSection.innerHTML = `
      <form id="apply-job-form" style="display:grid;gap:12px;text-align:left;">
        <h4 style="margin:0;">Submit Application</h4>
        <textarea id="app-cover-letter" placeholder="Cover statement or message to employer..." rows="3" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--bd);box-sizing:border-box;font-family:inherit;"></textarea>
        <div>
          <label style="font-size:13px;font-weight:600;display:block;margin-bottom:4px;">Upload CV / Résumé (PDF, DOCX, max 5MB)</label>
          <input type="file" id="app-cv-file" accept=".pdf,.doc,.docx" required style="width:100%;">
        </div>
        <div>
          <label style="font-size:13px;font-weight:600;display:block;margin-bottom:4px;">Supporting Certificate / Trade Test (Optional)</label>
          <input type="file" id="app-cert-file" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" style="width:100%;">
        </div>
        <button class="btn" type="submit" id="btn-submit-app">Submit Official Application</button>
        <div id="apply-toast" style="display:none;padding:10px;border-radius:8px;font-size:13px;"></div>
      </form>
    `;

    document.getElementById("apply-job-form").onsubmit = async (e) => {
      e.preventDefault();
      const btn = document.getElementById("btn-submit-app");
      const toast = document.getElementById("apply-toast");
      btn.disabled = true;
      btn.textContent = "Submitting application...";
      toast.style.display = "none";

      try {
        const cover = document.getElementById("app-cover-letter").value;
        const appRes = await window.apiClient.submitApplication(jobId, cover);

        // Upload CV
        const cvFile = document.getElementById("app-cv-file").files[0];
        if (cvFile) {
          btn.textContent = "Uploading CV...";
          await window.apiClient.uploadDocument(appRes.id, "cv", cvFile);
        }

        // Upload Cert if present
        const certFile = document.getElementById("app-cert-file").files[0];
        if (certFile) {
          btn.textContent = "Uploading certificate...";
          await window.apiClient.uploadDocument(appRes.id, "certificate", certFile);
        }

        toast.style.background = "#e6f7ec";
        toast.style.color = "#14703a";
        toast.style.display = "block";
        toast.innerHTML = "<b>Application Submitted!</b><br>Your profile and documents have been securely sent for contractor review.";
        btn.textContent = "Application Complete ✓";
      } catch (err) {
        toast.style.background = "#fee2e2";
        toast.style.color = "#b91c1c";
        toast.style.display = "block";
        toast.textContent = "Error: " + err.message;
        btn.disabled = false;
        btn.textContent = "Submit Official Application";
      }
    };
  } catch (err) {
    appSection.innerHTML = `<div style="color:#b91c1c;padding:12px;">Failed to verify access: ${err.message}</div>`;
  }
}

let _envPromise = null;
function getEnvironment() {
  // Fails safe to "production" so the mock-confirm option is never offered if /health is unreachable.
  if (!_envPromise) {
    _envPromise = fetch("/health").then(r => r.json()).then(h => h.environment).catch(() => "production");
  }
  return _envPromise;
}

async function triggerMpesaPaymentModal() {
  const phone = prompt("Confirm your Safaricom M-Pesa phone number for KSh 1,000 prompt (e.g. 0712345678):");
  if (!phone) return;

  try {
    const payRes = await window.apiClient.initiatePayment(phone);
    const paymentId = payRes.id;

    const env = await getEnvironment();
    if (env === "production") {
      alert(
        `An M-Pesa prompt for KSh 1,000 has been sent to ${phone}.\n\n` +
        `Enter your M-Pesa PIN on your phone. Your access unlocks automatically once the payment is confirmed. ` +
        `Refresh this page afterwards.`
      );
      return;
    }

    const confirmSim = confirm(
      `M-Pesa STK push initiated to ${phone} for KSh 1,000.\n\n` +
      `[TEST MODE]: Confirm this payment now via the mock provider?`
    );

    if (confirmSim) {
      await window.apiClient.mockConfirmPayment(paymentId);
      alert("Payment verified successfully! Platform access unlocked.");
      if (selectedJobForApply) {
        startApplicationFlow(selectedJobForApply.id);
      }
      checkAuthSession();
    } else {
      alert("Payment awaiting confirmation. You can check back once completed.");
    }
  } catch (err) {
    alert("Payment initiation failed: " + err.message);
  }
}

function setupRegistrationForm() {
  const form = document.getElementById("f");
  if (!form) return;

  form.onsubmit = async (e) => {
    e.preventDefault();
    const toast = document.getElementById("t");
    const btn = form.querySelector("button[type='submit']");
    btn.disabled = true;
    btn.textContent = "Processing...";
    toast.style.display = "none";

    const fullName = document.getElementById("nm").value;
    const phoneInput = form.querySelector("input[type='tel']").value;
    const emailInput = form.querySelector("input[type='email']").value;
    const password = document.getElementById("reg-pass").value;
    const selects = form.querySelectorAll("select");
    const trade = selects[0].value;
    const preferredCountry = selects[1].value;

    try {
      const regRes = await window.apiClient.register({
        full_name: fullName,
        phone: phoneInput,
        email: emailInput || null,
        trade: trade,
        preferred_country: preferredCountry,
        password: password
      });

      toast.style.background = "#e6f7ec";
      toast.style.color = "#14703a";
      toast.style.display = "block";

      // If mock OTP provided, prompt worker to verify seamlessly
      let otpCode = regRes.mock_otp;
      if (otpCode) {
        const userOtp = prompt(
          `Registration received!\nAn SMS OTP code has been sent to ${regRes.phone}.\n` +
          `[DEMO MODE OTP CODE: ${otpCode}]\n\nEnter your OTP code to verify ownership:`,
          otpCode
        );
        if (userOtp) {
          const authRes = await window.apiClient.verifyPhone(regRes.phone, userOtp);
          window.apiClient.setToken(authRes.access_token);
          toast.innerHTML = `<b>Welcome, ${escapeHtml(fullName.split(" ")[0])}!</b> Phone verified. Unlocking platform...`;
          
          // Trigger payment prompt
          setTimeout(() => {
            triggerMpesaPaymentModal();
          }, 1000);
          checkAuthSession();
          return;
        }
      }

      toast.textContent = regRes.message;
    } catch (err) {
      toast.style.background = "#fee2e2";
      toast.style.color = "#b91c1c";
      toast.style.display = "block";
      toast.textContent = "Registration failed: " + err.message;
    } finally {
      btn.disabled = false;
      btn.textContent = "Create account & pay KSh 1,000";
    }
  };
}

function showAuthTab(tab) {
  const panelSignup = document.getElementById("auth-panel-signup");
  const panelSignin = document.getElementById("auth-panel-signin");
  const btnSignup = document.getElementById("tab-btn-signup");
  const btnSignin = document.getElementById("tab-btn-signin");

  if (!panelSignup || !panelSignin) {
    console.warn("Auth panels not found");
    return;
  }

  if (tab === "signin") {
    panelSignup.style.setProperty("display", "none", "important");
    panelSignin.style.setProperty("display", "block", "important");
    if (btnSignin) {
      btnSignin.style.background = "#fff";
      btnSignin.style.color = "var(--navy)";
      btnSignin.style.borderBottom = "2px solid var(--navy)";
    }
    if (btnSignup) {
      btnSignup.style.background = "#f8fafc";
      btnSignup.style.color = "var(--mut)";
      btnSignup.style.borderBottom = "2px solid transparent";
    }
  } else {
    panelSignup.style.setProperty("display", "block", "important");
    panelSignin.style.setProperty("display", "none", "important");
    if (btnSignup) {
      btnSignup.style.background = "#fff";
      btnSignup.style.color = "var(--navy)";
      btnSignup.style.borderBottom = "2px solid var(--navy)";
    }
    if (btnSignin) {
      btnSignin.style.background = "#f8fafc";
      btnSignin.style.color = "var(--mut)";
      btnSignin.style.borderBottom = "2px solid transparent";
    }
  }
}
window.showAuthTab = showAuthTab;

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "🙈";
  } else {
    input.type = "password";
    btn.textContent = "👁️";
  }
}
window.togglePasswordVisibility = togglePasswordVisibility;

function setupSignInForm() {
  const form = document.getElementById("form-signin");
  if (!form) return;

  form.onsubmit = async (e) => {
    e.preventDefault();
    const phone = document.getElementById("signin-phone").value;
    const password = document.getElementById("signin-pass").value;
    const toast = document.getElementById("signin-toast");
    const btn = document.getElementById("btn-signin");

    btn.disabled = true;
    btn.textContent = "Signing in...";
    toast.style.display = "none";

    try {
      const authRes = await window.apiClient.login(phone, password);
      window.apiClient.setToken(authRes.access_token);
      toast.style.background = "#e6f7ec";
      toast.style.color = "#14703a";
      toast.style.display = "block";
      toast.textContent = "Signed in successfully! Redirecting to dashboard...";
      const isStaff = authRes.role === "administrator" || authRes.role === "reviewer";
      setTimeout(() => {
        window.location.href = isStaff ? "/admin" : "/dashboard";
      }, 700);
    } catch (err) {
      toast.style.background = "#fee2e2";
      toast.style.color = "#b91c1c";
      toast.style.display = "block";
      toast.textContent = "Sign in failed: " + err.message;
      btn.disabled = false;
      btn.textContent = "Sign In to Dashboard \u2192";
    }
  };
}

async function checkAuthSession() {
  const token = window.apiClient.getToken();
  const userPill = document.getElementById("user-nav-pill");
  const navLinks = document.querySelector("nav .w div");
  if (!userPill) return;

  if (!token) {
    userPill.style.display = "none";
    return;
  }

  try {
    const profile = await window.apiClient.getMyProfile();
    const access = await window.apiClient.getMyAccess();
    
    // Hide default Sign In / Create Account buttons when logged in
    const authBtns = document.querySelectorAll("nav .btn");
    authBtns.forEach(b => b.style.display = "none");

    userPill.style.display = "flex";
    userPill.style.alignItems = "center";
    userPill.style.gap = "8px";

    const statusBadge = access.is_activated 
      ? `<span style="background:#e6f7ec;color:#14703a;padding:4px 8px;border-radius:6px;font-size:12px;font-weight:700;">Active</span>`
      : `<span style="background:#fef3c7;color:#92400e;padding:4px 8px;border-radius:6px;font-size:12px;font-weight:700;">Locked</span>`;

    userPill.innerHTML = `
      <a href="/dashboard" style="font-size:14px;font-weight:700;color:var(--navy);text-decoration:none;">👤 ${escapeHtml(profile.full_name.split(" ")[0])}</a>
      ${statusBadge}
      <a href="/dashboard" class="btn s" style="margin-left:6px;">My Dashboard</a>
      <button class="btn s o" onclick="signOutWorker()" style="padding:5px 10px;font-size:12px;margin-left:4px;">Sign Out</button>
    `;
  } catch (err) {
    window.apiClient.setToken(null);
    userPill.style.display = "none";
    const authBtns = document.querySelectorAll("nav .btn");
    authBtns.forEach(b => b.style.display = "inline-block");
  }
}

async function signOutWorker() {
  try {
    await window.apiClient.logout();
  } catch(e) {}
  window.apiClient.setToken(null);
  window.location.reload();
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

// Auto-boot on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initTopLineApp);
} else {
  initTopLineApp();
}

