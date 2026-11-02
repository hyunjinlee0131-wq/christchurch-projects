// Site-wide settings that are public (not secrets).
/** The Streamlit app with the interactive tools. Empty → pages say "coming soon". */
export const STREAMLIT_URL: string = (import.meta.env.PUBLIC_STREAMLIT_URL ?? "").replace(/\/$/, "");
