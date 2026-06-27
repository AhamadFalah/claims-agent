import type { ClaimFormValues } from './types.ts';

// The n8n webhook URL is supplied at build time via Vite env vars.
// See .env.example. This must be the n8n endpoint, NOT the Attio API —
// the Attio token lives only inside n8n, never in this browser bundle.
const WEBHOOK_URL = import.meta.env.VITE_N8N_WEBHOOK_URL as string | undefined;

export async function submitClaim(values: ClaimFormValues, photo: File): Promise<void> {
  if (!WEBHOOK_URL) {
    throw new Error(
      'Form is not configured: VITE_N8N_WEBHOOK_URL is missing. Set it in your .env file.',
    );
  }

  // multipart/form-data so the photo binary streams through to n8n's
  // Webhook node (Binary Data enabled), which forwards it to POST /v2/files.
  const body = new FormData();
  body.append('name', values.name.trim());
  body.append('email', values.email.trim());
  body.append('phone_number', values.phone_number.trim());
  body.append('order_number', values.order_number.trim());
  body.append('courier', values.courier);
  body.append('claim_type', values.claim_type);
  body.append('parcel_count', values.parcel_count.trim());
  body.append('tracking_number', values.tracking_number.trim());
  body.append('additional_tracking', values.additional_tracking.trim());
  body.append('delivery_postcode', values.delivery_postcode.trim().toUpperCase());
  body.append('customer_comment', values.customer_comment.trim());
  body.append('parcel_value', values.parcel_value.trim());
  body.append('photo', photo, photo.name);

  let response: Response;
  try {
    response = await fetch(WEBHOOK_URL, { method: 'POST', body });
  } catch (err) {
    // Network-level failure (offline, CORS, DNS, etc.)
    console.error('Claim submission network error', err);
    throw new Error('We could not reach the server. Please check your connection and try again.');
  }

  if (!response.ok) {
    console.error('Claim submission failed', response.status);
    throw new Error(
      `Submission failed (status ${response.status}). Please try again, or contact support if it continues.`,
    );
  }
}
