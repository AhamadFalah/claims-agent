import { ClaimForm } from './ClaimForm.tsx';

export function App() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Submit a Parcel Claim</h1>
        <p className="subtitle">
          Tell us what went wrong with your delivery and we'll start a claim for you.
          Fields marked <span className="req">*</span> are required.
        </p>
      </header>
      <main>
        <ClaimForm />
      </main>
      <footer className="page-footer">
        <p>Your details are only used to process this claim.</p>
      </footer>
    </div>
  );
}
