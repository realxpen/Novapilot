import { Navbar } from "@/components/navbar";
import {
  Laptop,
  Smartphone,
  Headphones,
  Home,
  Gamepad2,
  Camera,
  Watch,
  Tv,
} from "lucide-react";
import Link from "next/link";

export default function CategoriesPage() {
  const categories = [
    {
      icon: <Laptop className="w-6 h-6 text-indigo-600" />,
      title: "Laptops & Computers",
      description: "Find the perfect machine for work, gaming, or general use.",
    },
    {
      icon: <Smartphone className="w-6 h-6 text-indigo-600" />,
      title: "Smartphones & Tablets",
      description: "Compare the latest mobile devices and their features.",
    },
    {
      icon: <Headphones className="w-6 h-6 text-indigo-600" />,
      title: "Audio & Headphones",
      description: "Discover the best sound quality for your budget.",
    },
    {
      icon: <Home className="w-6 h-6 text-indigo-600" />,
      title: "Smart Home",
      description: "Automate your life with top-rated smart devices.",
    },
    {
      icon: <Gamepad2 className="w-6 h-6 text-indigo-600" />,
      title: "Gaming & Consoles",
      description: "Level up your setup with the best gaming gear.",
    },
    {
      icon: <Camera className="w-6 h-6 text-indigo-600" />,
      title: "Photography & Cameras",
      description: "Capture memories with the perfect camera.",
    },
    {
      icon: <Watch className="w-6 h-6 text-indigo-600" />,
      title: "Wearables",
      description: "Track your fitness and stay connected on the go.",
    },
    {
      icon: <Tv className="w-6 h-6 text-indigo-600" />,
      title: "TVs & Home Theater",
      description: "Upgrade your entertainment experience.",
    },
  ];

  return (
    <div className="min-h-screen flex flex-col relative bg-zinc-50/50">
      <Navbar />

      <main className="flex-1 flex flex-col items-center pt-32 pb-20 px-4 sm:px-8">
        <div className="w-full max-w-4xl mx-auto text-center mb-16">
          <h1 className="text-4xl sm:text-6xl font-display font-bold tracking-tight text-zinc-900 mb-6">
            Explore Categories
          </h1>
          <p className="text-lg text-zinc-500 max-w-2xl mx-auto">
            NovaPilot can help you find the best products across a wide range of
            categories. Select a category to see popular searches or start your own.
          </p>
        </div>

        <div className="w-full max-w-6xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {categories.map((category, index) => (
            <Link
              key={index}
              href="/"
              className="bg-white rounded-3xl p-6 shadow-sm border border-zinc-200 hover:border-indigo-300 hover:shadow-md transition-all group flex flex-col h-full"
            >
              <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center mb-4 group-hover:bg-indigo-100 transition-colors">
                {category.icon}
              </div>
              <h3 className="text-lg font-bold text-zinc-900 mb-2">
                {category.title}
              </h3>
              <p className="text-sm text-zinc-500 leading-relaxed flex-1">
                {category.description}
              </p>
              <div className="mt-6 text-sm font-medium text-indigo-600 group-hover:text-indigo-700 flex items-center gap-1">
                Explore Category
                <span className="group-hover:translate-x-1 transition-transform">
                  →
                </span>
              </div>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
