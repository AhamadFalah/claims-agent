import type { ClaimFormValues, FormErrors } from './types.ts';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// Accepts most UK postcode shapes (case/space insensitive).
const UK_POSTCODE_RE = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i;
const MAX_PHOTO_BYTES = 10 * 1024 * 1024; // 10 MB

export function validate(values: ClaimFormValues, photo: File | null): FormErrors {
  const errors: FormErrors = {};

  if (!values.name.trim()) {
    errors.name = 'Please enter your full name.';
  }

  if (!values.email.trim()) {
    errors.email = 'Please enter your email address.';
  } else if (!EMAIL_RE.test(values.email.trim())) {
    errors.email = 'Please enter a valid email address.';
  }

  if (!values.phone_number.trim()) {
    errors.phone_number = 'Please enter a contact phone number.';
  }

  if (!values.order_number.trim()) {
    errors.order_number = 'Please enter your order number.';
  }

  if (!values.courier) {
    errors.courier = 'Please select the courier.';
  }

  if (!values.claim_type) {
    errors.claim_type = 'Please tell us if the parcel was lost or damaged.';
  }

  const parcelCount = Number(values.parcel_count);
  if (!values.parcel_count.trim() || !Number.isInteger(parcelCount) || parcelCount < 1) {
    errors.parcel_count = 'Enter the number of parcels (1 or more).';
  }

  if (!values.tracking_number.trim()) {
    errors.tracking_number = 'Please enter the tracking number.';
  }

  if (!values.delivery_postcode.trim()) {
    errors.delivery_postcode = 'Please enter the delivery postcode.';
  } else if (!UK_POSTCODE_RE.test(values.delivery_postcode.trim())) {
    errors.delivery_postcode = 'Please enter a valid UK postcode.';
  }

  if (!values.customer_comment.trim()) {
    errors.customer_comment = 'Please describe what happened.';
  }

  const value = Number(values.parcel_value);
  if (!values.parcel_value.trim() || Number.isNaN(value) || value <= 0) {
    errors.parcel_value = 'Enter the cost value of the claim.';
  }

  if (!photo) {
    errors.photo = 'Please attach a photo supporting your claim.';
  } else if (photo.size > MAX_PHOTO_BYTES) {
    errors.photo = 'Photo must be 10 MB or smaller.';
  } else if (!photo.type.startsWith('image/')) {
    errors.photo = 'Please attach an image file.';
  }

  return errors;
}
