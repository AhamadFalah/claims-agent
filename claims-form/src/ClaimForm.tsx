import { useState, type ChangeEvent, type FormEvent } from 'react';
import {
  CLAIM_TYPES,
  COURIERS,
  INITIAL_VALUES,
  type ClaimFormValues,
  type FormErrors,
  type SubmitState,
} from './types.ts';
import { validate } from './validation.ts';
import { submitClaim } from './submitClaim.ts';

export function ClaimForm() {
  const [values, setValues] = useState<ClaimFormValues>(INITIAL_VALUES);
  const [photo, setPhoto] = useState<File | null>(null);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submit, setSubmit] = useState<SubmitState>({ status: 'idle' });

  function update(field: keyof ClaimFormValues) {
    return (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      setValues((prev) => ({ ...prev, [field]: e.target.value }));
      // Clear a field's error as soon as the user edits it.
      setErrors((prev) => (prev[field] ? { ...prev, [field]: undefined } : prev));
    };
  }

  function onPhotoChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setPhoto(file);
    setErrors((prev) => (prev.photo ? { ...prev, photo: undefined } : prev));
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();

    const nextErrors = validate(values, photo);
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      setSubmit({ status: 'idle' });
      return;
    }

    setSubmit({ status: 'submitting' });
    try {
      // photo is guaranteed non-null here because validate() requires it.
      await submitClaim(values, photo as File);
      setSubmit({ status: 'success' });
      setValues(INITIAL_VALUES);
      setPhoto(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong. Please try again.';
      setSubmit({ status: 'error', message });
    }
  }

  if (submit.status === 'success') {
    return (
      <div className="card success-card" role="status">
        <h2>Claim received ✅</h2>
        <p>
          Thanks — we've logged your claim and our team will be in touch by email.
          Keep your tracking number handy in case we need more detail.
        </p>
        <button type="button" className="btn" onClick={() => setSubmit({ status: 'idle' })}>
          Submit another claim
        </button>
      </div>
    );
  }

  const isSubmitting = submit.status === 'submitting';

  return (
    <form className="card" onSubmit={onSubmit} noValidate>
      <Field label="Full name" htmlFor="name" required error={errors.name}>
        <input
          id="name"
          type="text"
          autoComplete="name"
          value={values.name}
          onChange={update('name')}
        />
      </Field>

      <div className="row">
        <Field label="Email address" htmlFor="email" required error={errors.email}>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={values.email}
            onChange={update('email')}
          />
        </Field>
        <Field label="Phone number" htmlFor="phone_number" required error={errors.phone_number}>
          <input
            id="phone_number"
            type="tel"
            autoComplete="tel"
            value={values.phone_number}
            onChange={update('phone_number')}
          />
        </Field>
      </div>

      <div className="row">
        <Field label="Order number" htmlFor="order_number" required error={errors.order_number}>
          <input
            id="order_number"
            type="text"
            value={values.order_number}
            onChange={update('order_number')}
          />
        </Field>
        <Field label="Courier" htmlFor="courier" required error={errors.courier}>
          <select id="courier" value={values.courier} onChange={update('courier')}>
            <option value="" disabled>
              Select a courier…
            </option>
            {COURIERS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="row">
        <Field label="Is this a claim for loss or damage?" htmlFor="claim_type" required error={errors.claim_type}>
          <select id="claim_type" value={values.claim_type} onChange={update('claim_type')}>
            <option value="" disabled>
              Select…
            </option>
            {CLAIM_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Number of parcels claimed" htmlFor="parcel_count" required error={errors.parcel_count}>
          <input
            id="parcel_count"
            type="number"
            min={1}
            step={1}
            value={values.parcel_count}
            onChange={update('parcel_count')}
          />
        </Field>
      </div>

      <Field label="Tracking number" htmlFor="tracking_number" required error={errors.tracking_number}>
        <input
          id="tracking_number"
          type="text"
          value={values.tracking_number}
          onChange={update('tracking_number')}
        />
      </Field>

      <Field
        label="More tracking numbers (if any)"
        htmlFor="additional_tracking"
        hint="One per line, for multi-parcel claims."
        error={errors.additional_tracking}
      >
        <textarea
          id="additional_tracking"
          rows={2}
          value={values.additional_tracking}
          onChange={update('additional_tracking')}
        />
      </Field>

      <div className="row">
        <Field
          label="Delivery destination postcode"
          htmlFor="delivery_postcode"
          required
          error={errors.delivery_postcode}
        >
          <input
            id="delivery_postcode"
            type="text"
            autoComplete="postal-code"
            value={values.delivery_postcode}
            onChange={update('delivery_postcode')}
          />
        </Field>
        <Field label="Cost value (£)" htmlFor="parcel_value" required error={errors.parcel_value}>
          <input
            id="parcel_value"
            type="number"
            min={0}
            step="0.01"
            value={values.parcel_value}
            onChange={update('parcel_value')}
          />
        </Field>
      </div>

      <Field
        label="What is the reason for your claim?"
        htmlFor="customer_comment"
        required
        error={errors.customer_comment}
      >
        <textarea
          id="customer_comment"
          rows={4}
          placeholder="Describe what happened with your delivery…"
          value={values.customer_comment}
          onChange={update('customer_comment')}
        />
      </Field>

      <Field
        label="Photographic evidence supporting your claim"
        htmlFor="photo"
        required
        hint="A clear photo of the damage or packaging. JPG/PNG, up to 10 MB."
        error={errors.photo}
      >
        <input id="photo" type="file" accept="image/*" onChange={onPhotoChange} />
        {photo && <span className="file-name">Selected: {photo.name}</span>}
      </Field>

      {submit.status === 'error' && (
        <p className="form-error" role="alert">
          {submit.message}
        </p>
      )}

      <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting…' : 'Submit claim'}
      </button>
    </form>
  );
}

interface FieldProps {
  label: string;
  htmlFor: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}

function Field({ label, htmlFor, required, hint, error, children }: FieldProps) {
  return (
    <div className={`field${error ? ' field-error' : ''}`}>
      <label htmlFor={htmlFor}>
        {label}
        {required && <span className="req"> *</span>}
      </label>
      {children}
      {hint && !error && <span className="hint">{hint}</span>}
      {error && (
        <span className="error-text" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
