declare const process: { env: Record<string, string | undefined> };

const baseUrl = (process.env.AIOGRAPI_REST_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const userId = process.env.AIOGRAPI_REST_USER_ID ?? "25025320";

function env(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value ? value : undefined;
}

async function postForm(path: string, fields: Record<string, string>): Promise<unknown> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(fields),
  });
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

async function getJson(path: string, sessionid: string): Promise<unknown> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      Accept: "application/json",
      "X-Session-ID": sessionid,
    },
  });
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

async function getSessionID(): Promise<string> {
  const savedSessionID = env("AIOGRAPI_REST_SESSIONID");
  if (savedSessionID) {
    return savedSessionID;
  }

  const instagramSessionID = env("AIOGRAPI_REST_INSTAGRAM_SESSIONID");
  if (instagramSessionID) {
    const value = await postForm("/auth/login/by/sessionid", { sessionid: instagramSessionID });
    if (typeof value === "string" && value) {
      return value;
    }
  }

  const username = env("AIOGRAPI_REST_USERNAME");
  const password = env("AIOGRAPI_REST_PASSWORD");
  if (username && password) {
    const fields: Record<string, string> = { username, password };
    const verificationCode = env("AIOGRAPI_REST_VERIFICATION_CODE");
    if (verificationCode) {
      fields.verification_code = verificationCode;
    }
    const value = await postForm("/auth/login", fields);
    if (typeof value === "string" && value) {
      return value;
    }
  }

  throw new Error(
    "Set AIOGRAPI_REST_SESSIONID, AIOGRAPI_REST_INSTAGRAM_SESSIONID, " +
      "or AIOGRAPI_REST_USERNAME/AIOGRAPI_REST_PASSWORD.",
  );
}

const about = await getJson(`/user/about?user_id=${encodeURIComponent(userId)}`, await getSessionID());
console.log(JSON.stringify(about, null, 2));

export {};
