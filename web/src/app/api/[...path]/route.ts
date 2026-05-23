import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest, props: { params: Promise<{ path: string[] }> }) {
  const params = await props.params;
  return proxyRequest(req, params.path);
}

export async function POST(req: NextRequest, props: { params: Promise<{ path: string[] }> }) {
  const params = await props.params;
  return proxyRequest(req, params.path);
}

export async function PUT(req: NextRequest, props: { params: Promise<{ path: string[] }> }) {
  const params = await props.params;
  return proxyRequest(req, params.path);
}

export async function DELETE(req: NextRequest, props: { params: Promise<{ path: string[] }> }) {
  const params = await props.params;
  return proxyRequest(req, params.path);
}

async function proxyRequest(req: NextRequest, pathSegments: string[]) {
  const targetBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  // Remove any trailing slash from targetBase
  const normalizedTargetBase = targetBase.replace(/\/$/, "");
  
  const path = pathSegments.join("/");
  const searchParams = req.nextUrl.searchParams.toString();
  const url = `${normalizedTargetBase}/${path}${searchParams ? `?${searchParams}` : ""}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!["host", "connection", "content-length"].includes(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const method = req.method;
  let body: any = undefined;

  if (["POST", "PUT", "PATCH"].includes(method)) {
    try {
      body = await req.blob();
    } catch {
      // No body or error reading it
    }
  }

  try {
    const res = await fetch(url, {
      method,
      headers,
      body,
      // @ts-ignore
      duplex: "half",
    });

    const responseHeaders = new Headers();
    res.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    return new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    });
  } catch (err: any) {
    console.error("Proxy error:", err);
    return NextResponse.json(
      { error: "Proxy connection failed", details: err.message },
      { status: 502 }
    );
  }
}
