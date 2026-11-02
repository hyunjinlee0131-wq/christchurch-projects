// Site-wide settings that are public (not secrets).
/** The Streamlit app with the interactive tools (override with PUBLIC_STREAMLIT_URL). */
export const STREAMLIT_URL: string = (
  import.meta.env.PUBLIC_STREAMLIT_URL || "https://christchurch-projects-gqxzcaapenuypjw8xkwmhf.streamlit.app"
).replace(/\/$/, "");
