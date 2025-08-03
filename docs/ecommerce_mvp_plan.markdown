# PlasmaProject E-Commerce MVP Plan
## Objective
Launch a minimally viable product (MVP) for `app.plasmatableburnouts.com` to enable customer payments, build trust, and generate cash flow, integrating with the existing PlasmaProject (v1-1-7) quoting app.

## Context
- **Current App**: PlasmaProject v1-1-7, Flask-based, with DXF parsing (`dxf_parser.py`), costing logic (`costing.py`), and React+Tailwind frontend.
- **Goal**: Add e-commerce features (payments, user accounts, order history) while preserving core quoting functionality.
- **User**: Non-developer entrepreneur (ENTP), needs clear, referenceable plan for Cascade and future Grok chats.
- **Tools**: Windsurf’s Cascade for code changes, Grok for strategic planning.

## Core Requirements
- **Payment Processing**: Secure payments via Stripe.
- **Order Confirmation**: Immediate order feedback.
- **Emailing Receipts**: Automated receipts to customers.
- **User Setup**: Firebase for signup/login.
- **User Database**: MongoDB for users/orders.
- **Order History**: Display past orders.
- **Integration**: Seamless with existing DXF parsing/costing.

## Tech Stack
- **Frontend**: React+Tailwind (existing `templates/`).
- **Backend**: Flask (existing `run.py`, `app/`).
- **Database**: MongoDB Atlas (free tier, 512MB).
- **Payment Processor**: Stripe (2.9% + $0.30/transaction).
- **Email Service**: `smtplib` (Gmail, free) or SendGrid (free tier).
- **Authentication**: Firebase Authentication (free tier).
- **Hosting**: Heroku (free tier) or GoDaddy cPanel.
- **Domain**: `app.plasmatableburnouts.com` (GoDaddy subdomain).
- **File Storage**: Cloudinary (free tier) or GoDaddy.

## Project Structure
```
PlasmaProject/
├── run.py                     # Flask entry point
├── app/
│   ├── __init__.py            # Flask config, MongoDB, Firebase
│   ├── routes/
│   │   ├── main.py            # Landing, quote, etc.
│   │   ├── auth.py            # Firebase signup/login
│   │   ├── payments.py        # Stripe payments
│   │   ├── orders.py          # Order history/confirmation
│   ├── models/                # MongoDB collections
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── order.py
│   │   ├── upload.py
│   ├── utils/
│   │   ├── costing.py
│   │   ├── dxf_parser.py
│   │   ├── email.py          # Receipt emailing
│   ├── static/
│   │   ├── assets/
│   │   │   ├── images/       # cutting-table.jpg, cut-parts.jpg
│   │   ├── logos/
│   ├── templates/
│   │   ├── landing.html       # React+Tailwind landing
│   │   ├── customer_index.html# Quote engine
│   │   ├── signup.html        # Firebase auth
│   │   ├── login.html         # Updated with Firebase
│   │   ├── order_confirmation.html
│   │   ├── order_history.html # Enhanced
│   │   ├── checkout.html      # Stripe integration
│   │   ├── error.html
│   │   ├── success.html
│   │   ├── terms.html
├── requirements.txt           # pymongo, stripe, firebase-admin
├── tailwind.config.js         # Frontend styling
├── package.json               # React dependencies
```

## Development Plan
### Week 1: Backend Setup
- **Tasks**:
  - Set up MongoDB Atlas (free tier).
  - Install `pymongo`, `firebase-admin` in `requirements.txt`.
  - Update `app/__init__.py` for MongoDB/Firebase.
  - Migrate `models/` to MongoDB collections (`user.py`, `order.py`, `upload.py`).
- **Cascade Prompt**: "Configure Flask app in `app/__init__.py` to connect to MongoDB Atlas and Firebase. Convert SQL models in `app/models/` to MongoDB collections. Preserve existing DXF parsing and costing logic."

### Week 2: Payment Integration
- **Tasks**:
  - Install `stripe` in `requirements.txt`.
  - Create `routes/payments.py` with Stripe Checkout.
  - Update `checkout.html` to redirect to Stripe.
  - Add webhook handler for payment confirmation.
  - Create `order_confirmation.html` for post-payment display.
- **Cascade Prompt**: "Integrate Stripe Checkout in `routes/payments.py`. Add webhook handler. Update `checkout.html` for Stripe redirect. Create `order_confirmation.html` to show order details, saving to MongoDB."

### Week 3: Authentication & Emailing
- **Tasks**:
  - Create `routes/auth.py` for Firebase signup/login.
  - Add `signup.html`, update `login.html` with Firebase.
  - Implement `utils/email.py` with `smtplib`/SendGrid for receipts.
  - Test email flow with order details.
- **Cascade Prompt**: "Add Firebase Authentication in `routes/auth.py`. Create `signup.html`, update `login.html`. Implement `utils/email.py` for receipt emails using `smtplib` or SendGrid."

### Week 4: Order History & Deployment
- **Tasks**:
  - Enhance `routes/orders.py` for order history API.
  - Update `order_history.html` with MongoDB queries.
  - Test full flow: quote, payment, confirmation, email, history.
  - Deploy to Heroku/GoDaddy (`app.plasmatableburnouts.com`).
- **Cascade Prompt**: "Create `routes/orders.py` for order history API. Update `order_history.html` to display orders from MongoDB. Deploy app to Heroku/GoDaddy with DNS setup for `app.plasmatableburnouts.com`."

## Testing
- **Local**: Run `python run.py` for Flask, `npm run dev` for React. Test quote, payment, signup, email, and history.
- **Staging**: Deploy to Heroku/GoDaddy, verify subdomain.
- **Tools**: Stripe Dashboard, MongoDB Atlas, Firebase Console.

## Budget
- **Free**: MongoDB Atlas, Firebase, Cloudinary, `smtplib`.
- **Low-Cost**: Stripe (2.9% + $0.30/transaction), Heroku (~$7/month if needed).
- **Existing**: GoDaddy hosting/subdomain.

## Notes for Cascade
- Preserve `costing.py`, `dxf_parser.py` functionality.
- Update files in-place unless specified.
- Test changes locally before committing.
- Provide clear commit messages (e.g., "Added Stripe Checkout to payments.py").

## Next Steps
- Save this plan in `PlasmaProject/docs/ecommerce_mvp_plan.md`.
- Create "PlasmaProject v1-1-7" workspace in Grok’s Projects tab.
- Upload all files and this plan to workspace.
- Start Week 1 tasks with Cascade.