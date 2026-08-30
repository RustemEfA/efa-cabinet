"use client";

import { useFormStatus } from "react-dom";

export function SubmitButton({ children }: { children: React.ReactNode }) {
  const { pending } = useFormStatus();
    return (
        <button className="btn" type="submit" disabled={pending}>
              {pending ? "Загрузка..." : children}
                  </button>
                    );
                    }
                    
