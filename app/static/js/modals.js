// Plain JS modal helpers for PlasmaProject
// Attach modal open/close helpers to window for all HTML buttons
window.openModal = (id) => {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('hidden');
};
window.closeModal = (id) => {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('hidden');
};

// Guest Checkout AJAX
function submitGuestCheckout(e) {
  e.preventDefault();
  const form = e.target;
  const data = {
    name: form.name.value,
    email: form.email.value,
    phone: form.phone.value,
    order_id: window.currentOrderId || null
  };
  fetch('/guest_checkout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
    .then(res => res.json())
    .then(res => {
      if (res.error) throw new Error(res.error);
      window.closeModal('guestCheckoutModal');
      window.openModal('paymentModal');
      setTimeout(window.initStripeElementsModal, 100);
    })
    .catch(err => alert('Guest checkout failed: ' + err.message));
}

// Login AJAX using Firebase SDK and Flask backend
function submitLogin(e) {
  e.preventDefault();
  const form = e.target;
  const email = form.email.value;
  const password = form.password.value;
  if (!email || !password) {
    alert('Please enter email and password.');
    return;
  }
  if (!window.firebase || !window.firebase.auth) {
    alert('Firebase SDK not loaded.');
    return;
  }
  window.firebase.auth().signInWithEmailAndPassword(email, password)
    .then(userCredential => userCredential.user.getIdToken())
    .then(idToken => fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken })
    }))
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        window.closeModal('loginModal');
        // Optionally update UI to show logged-in state
        location.reload();
      } else {
        alert(data.error || 'Login failed.');
      }
    })
    .catch(err => alert('Login failed: ' + err.message));
}

// Signup AJAX using Firebase SDK and Flask backend
function submitSignup(e) {
  e.preventDefault();
  const form = e.target;
  const email = form.email.value;
  const password = form.password.value;
  if (!email || !password) {
    alert('Please enter email and password.');
    return;
  }
  if (!window.firebase || !window.firebase.auth) {
    alert('Firebase SDK not loaded.');
    return;
  }
  window.firebase.auth().createUserWithEmailAndPassword(email, password)
    .then(userCredential => userCredential.user.getIdToken())
    .then(idToken => fetch('/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken })
    }))
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        window.closeModal('signupModal');
        // Optionally update UI to show logged-in state
        location.reload();
      } else {
        alert(data.error || 'Signup failed.');
      }
    })
    .catch(err => alert('Signup failed: ' + err.message));
}

// Payment Modal (Stripe Elements)
window.initStripeElementsModal = async function () {
  // Unmount previous card if remounting
  if (window._stripeCard && window._stripeCard.destroy) {
    try { window._stripeCard.destroy(); } catch (e) {}
    document.getElementById('card-element').innerHTML = '';
    window._stripeCardMounted = false;
  }
  if (!window.Stripe) {
    alert('Stripe.js not loaded.');
    return;
  }
  const stripe = Stripe(document.body.getAttribute('data-stripe-public-key'));
  if (!stripe) {
    document.getElementById('card-errors').textContent = 'Stripe public key missing.';
    return;
  }
  // Prevent double-mount
  if (window._stripeCardMounted) return;
  window._stripeCardMounted = true;
  const elements = stripe.elements();
  const card = elements.create('card', {
    style: { base: { fontSize: '18px', color: '#fff', '::placeholder': { color: '#bdbdbd' } } }
  });
  card.mount('#card-element');
  card.on('change', function(event) {
    document.getElementById('card-errors').textContent = event.error ? event.error.message : '';
  });
  const form = document.getElementById('stripePaymentForm');
  form.onsubmit = async function (e) {
    e.preventDefault();
    document.getElementById('payNowBtn').disabled = true;
    document.getElementById('payNowBtn').textContent = 'Processing...';
    document.getElementById('payment-success').classList.add('hidden');
    document.getElementById('payment-failure').classList.add('hidden');
    try {
      // Fetch PaymentIntent client secret
      const orderId = window.currentOrderId || document.body.getAttribute('data-order-id');
      const resp = await fetch('/create-payment-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId })
      });
      const { clientSecret, error } = await resp.json();
      if (!clientSecret) throw new Error(error || 'Unable to start payment.');
      // Confirm card payment
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: card,
          billing_details: {
            name: document.getElementById('first_name')?.value + ' ' + document.getElementById('last_name')?.value,
            email: document.getElementById('email')?.value
          }
        }
      });
      if (result.error) {
        document.getElementById('card-errors').textContent = result.error.message;
        document.getElementById('payment-failure').textContent = result.error.message;
        document.getElementById('payment-failure').classList.remove('hidden');
        document.getElementById('payNowBtn').disabled = false;
        document.getElementById('payNowBtn').textContent = 'Pay Now';
        return;
      }
      // Confirm payment with backend
      const confirmResp = await fetch('/confirm-payment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_intent_id: result.paymentIntent.id, order_id: orderId })
      });
      const confirmData = await confirmResp.json();
      if (confirmData.status === 'success') {
        document.getElementById('payment-success').textContent = 'Payment successful! Redirecting...';
        document.getElementById('payment-success').classList.remove('hidden');
        setTimeout(() => { window.location.href = '/order_confirmation'; }, 1500);
      } else {
        document.getElementById('payment-failure').textContent = confirmData.error || 'Payment failed.';
        document.getElementById('payment-failure').classList.remove('hidden');
        document.getElementById('payNowBtn').disabled = false;
        document.getElementById('payNowBtn').textContent = 'Pay Now';
      }
    } catch (err) {
      document.getElementById('payment-failure').textContent = err.message;
      document.getElementById('payment-failure').classList.remove('hidden');
      document.getElementById('payNowBtn').disabled = false;
      document.getElementById('payNowBtn').textContent = 'Pay Now';
    }
  };
};

// Attach form handlers
window.addEventListener('DOMContentLoaded', () => {
  const guestForm = document.getElementById('guestCheckoutForm');
  if (guestForm) guestForm.onsubmit = submitGuestCheckout;
  const loginForm = document.getElementById('loginForm');
  if (loginForm) loginForm.onsubmit = submitLogin;
  const signupForm = document.getElementById('signupForm');
  if (signupForm) signupForm.onsubmit = submitSignup;
});