// Guest Checkout Payment Flow (Stripe)
// Handles guest info form submission, creates Stripe Checkout session, and redirects to payment

document.addEventListener('DOMContentLoaded', function () {
    const stripe = Stripe(window.STRIPE_PUBLIC_KEY || (typeof STRIPE_PUBLIC_KEY !== 'undefined' ? STRIPE_PUBLIC_KEY : ''));
    const form = document.getElementById('guest-checkout-form');
    const processing = document.getElementById('processing');
    const message = document.getElementById('payment-message');

    if (!form) return;

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        form.style.display = 'none';
        if (processing) processing.style.display = 'block';

        const formData = {
            company_name: document.getElementById('company_name').value,
            first_name: document.getElementById('first_name').value,
            last_name: document.getElementById('last_name').value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value
        };

        try {
            // Save guest info and create Stripe session in one call
            const response = await fetch('/checkout_process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Redirect to Stripe Checkout
            const result = await stripe.redirectToCheckout({ sessionId: data.session_id });
            if (result.error) {
                throw new Error(result.error.message);
            }
        } catch (error) {
            form.style.display = 'block';
            if (processing) processing.style.display = 'none';
            if (message) message.textContent = 'Error: ' + error.message;
        }
    });
});
