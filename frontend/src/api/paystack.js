import PaystackPop from '@paystack/inline-js';

/**
 * Open Paystack inline checkout popup using the server-generated access code.
 *
 * @param {Object} options
 * @param {string} options.accessCode - Access code returned by /api/public/initialize-payment
 * @param {Function} [options.onSuccess] - Callback when customer completes payment: ({ id, reference, message })
 * @param {Function} [options.onCancel] - Callback when customer closes modal without completing payment
 * @param {Function} [options.onError] - Callback on error: ({ message })
 */
export function openPaystackCheckout({ accessCode, onSuccess, onCancel, onError }) {
  if (!accessCode) {
    console.error('Cannot open Paystack checkout: accessCode is missing.');
    if (onError) onError({ message: 'Payment access code missing.' });
    return null;
  }

  try {
    const popup = new PaystackPop();
    return popup.resumeTransaction(accessCode, {
      onSuccess: (transaction) => {
        if (onSuccess) onSuccess(transaction);
      },
      onCancel: () => {
        if (onCancel) onCancel();
      },
      onError: (err) => {
        console.error('Paystack transaction error:', err);
        if (onError) onError(err);
      },
    });
  } catch (error) {
    console.error('Failed to initialize Paystack inline popup:', error);
    if (onError) onError({ message: error.message });
    return null;
  }
}
