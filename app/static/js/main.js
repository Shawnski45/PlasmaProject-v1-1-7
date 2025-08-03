// Main entry point for Vite
import '../css/input.css';

// Import other JS modules
import './guest_checkout';
import './modals';

// Enable HMR in development
if (import.meta.hot) {
  import.meta.hot.accept();
}

console.log('Vite is working!');
