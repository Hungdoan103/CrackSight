import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "InfraVision AI - Hệ thống báo cáo vết nứt cơ sở hạ tầng",
  description: "DeepInspect + Qwen3-VL: mask nứt thật, mm/GPS chỉ từ CSV+EXIF.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        <link rel="stylesheet" href="/infravision.css?v=38" />
      </head>
      <body>{children}</body>
    </html>
  );
}
