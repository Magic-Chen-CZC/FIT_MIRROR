"use client"

import React from "react"; // 修复 React 导入问题
import { MenuIcon, ChevronDown, ChevronUp } from "lucide-react";
import Image from "next/image";
import { useState } from "react";

export default function ChineseWorkoutsPage() {
  const [openWorkout, setOpenWorkout] = useState<string | null>(null)

  const toggleWorkout = (workout: string) => {
    if (openWorkout === workout) {
      setOpenWorkout(null)
    } else {
      setOpenWorkout(workout)
    }
  }

  return (
    <div className="p-6 pb-20">
      <div className="flex justify-between items-center mb-4">
        <MenuIcon className="text-[#1c1b1f]" />
      </div>

      <h1 className="text-2xl font-semibold mb-4 text-[#1c1b1f]">All Workouts</h1>

      <div className="relative mb-6">
        <input
          type="text"
          className="w-full bg-white rounded-full py-3 px-12 border border-[#d9d9d9]"
          placeholder="Search"
        />
        <div className="absolute left-4 top-1/2 transform -translate-y-1/2">
          <Search className="w-5 h-5 text-[#676565]" />
        </div>
      </div>

      <div className="space-y-8">
        {/* Evening Workout Card */}
        <div>
          <div
            className="bg-[#e4dafa] rounded-xl p-4 flex items-center cursor-pointer"
            onClick={() => toggleWorkout("evening")}
          >
            <div className="w-20 h-20 relative mr-4">
              <Image
                src="/placeholder.svg?height=80&width=80"
                alt="Evening Workout"
                width={80}
                height={80}
                className="object-cover"
              />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-medium text-[#1c1b1f]">晚间锻炼</h3>
              <p className="text-sm text-[#676565]">+25 分钟</p>
            </div>
            <div className="p-1 rounded-full bg-white">
              {openWorkout === "evening" ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </div>
          </div>

          {/* Evening Workout Exercises */}
          <div
            className={`space-y-3 overflow-hidden transition-all duration-300 mt-3 ${
              openWorkout === "evening" ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0"
            }`}
          >
            {eveningExercises.map((exercise, index) => (
              <div key={index}>
                <ExerciseCard exercise={exercise} />
              </div>
            ))}
          </div>
        </div>

        {/* Exercise Categories */}
        <div className="border-t border-[#d9d9d9] py-2">
          <div className="py-2 border-b border-[#d9d9d9]">
            <h3 className="font-medium">深蹲</h3>
          </div>
          <div className="py-2 border-b border-[#d9d9d9]">
            <h3 className="font-medium">仰卧起坐</h3>
          </div>
          <div className="py-2 border-b border-[#d9d9d9]">
            <h3 className="font-medium">俯卧撑</h3>
          </div>
          <div className="py-2 border-b border-[#d9d9d9]">
            <h3 className="font-medium">跑步</h3>
          </div>
          <div className="py-2 border-b border-[#d9d9d9]">
            <h3 className="font-medium">引体向上</h3>
          </div>
        </div>

        {/* Night Stretches Card */}
        <div>
          <div
            className="bg-[#e4dafa] rounded-xl p-4 flex items-center cursor-pointer"
            onClick={() => toggleWorkout("night")}
          >
            <div className="w-20 h-20 relative mr-4">
              <Image
                src="/placeholder.svg?height=80&width=80"
                alt="Night Stretches"
                width={80}
                height={80}
                className="object-cover"
              />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-medium text-[#1c1b1f]">夜间拉伸</h3>
              <p className="text-sm text-[#676565]">+15 分钟</p>
            </div>
            <div className="p-1 rounded-full bg-white">
              {openWorkout === "night" ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </div>
          </div>

          {/* Night Stretches Exercises */}
          <div
            className={`space-y-3 overflow-hidden transition-all duration-300 mt-3 ${
              openWorkout === "night" ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0"
            }`}
          >
            {nightStretches.map((stretch, index) => (
              <div key={index}>
                <StretchCard stretch={stretch} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

interface Exercise {
  name: string
  sets: number
  reps: number
  rest: number
  image: string
}

const eveningExercises: Exercise[] = [
  {
    name: "深蹲",
    sets: 3,
    reps: 12,
    rest: 60,
    image: "/placeholder.svg?height=80&width=80",
  },
  {
    name: "俯卧撑",
    sets: 3,
    reps: 10,
    rest: 45,
    image: "/placeholder.svg?height=80&width=80",
  },
  {
    name: "弓步蹲",
    sets: 3,
    reps: 10,
    rest: 45,
    image: "/placeholder.svg?height=80&width=80",
  },
  {
    name: "平板支撑",
    sets: 3,
    reps: 30,
    rest: 30,
    image: "/placeholder.svg?height=80&width=80",
  },
  {
    name: "哑铃划船",
    sets: 3,
    reps: 12,
    rest: 60,
    image: "/placeholder.svg?height=80&width=80",
  },
]

interface Stretch {
  name: string
  duration: number
  image: string
}

const nightStretches: Stretch[] = [
  {
    name: "颈部拉伸",
    duration: 30,
    image: "/placeholder.svg?height=80&width=80",
  },
  {
    name: "肩部拉伸",
    duration: 45,
    image: "/placeholder.svg?height=80&width=80",
  },
  {
    name: "腿筋拉伸",
    duration: 60,
    image: "/placeholder.svg?height=80&width=80",
  },
  {
    name: "下背部拉伸",
    duration: 45,
    image: "/placeholder.svg?height=80&width=80",
  },
  {
    name: "髋部拉伸",
    duration: 60,
    image: "/placeholder.svg?height=80&width=80",
  },
]

function ExerciseCard({ exercise }: { exercise: Exercise }) {
  return (
    <div className="bg-white rounded-xl p-4 flex items-center animate-fadeIn">
      <div className="w-16 h-16 relative mr-4 bg-[#f5f5f5] rounded-lg flex items-center justify-center">
        <Image
          src={exercise.image || "/placeholder.svg"}
          alt={exercise.name}
          width={50}
          height={50}
          className="object-cover"
        />
      </div>
      <div className="flex-1">
        <h3 className="font-medium">{exercise.name}</h3>
        <p className="text-sm text-[#676565]">
          {exercise.sets} 组 • {exercise.reps} {exercise.name === "平板支撑" ? "秒" : "次"}
        </p>
      </div>
      <div className="bg-[#f5f5f5] px-3 py-1 rounded-full text-sm">休息 {exercise.rest}秒</div>
    </div>
  )
}

function StretchCard({ stretch }: { stretch: Stretch }) {
  return (
    <div className="bg-white rounded-xl p-4 flex items-center animate-fadeIn">
      <div className="w-16 h-16 relative mr-4 bg-[#f5f5f5] rounded-lg flex items-center justify-center">
        <Image
          src={stretch.image || "/placeholder.svg"}
          alt={stretch.name}
          width={50}
          height={50}
          className="object-cover"
        />
      </div>
      <div className="flex-1">
        <h3 className="font-medium">{stretch.name}</h3>
        <p className="text-sm text-[#676565]">保持 {stretch.duration} 秒</p>
      </div>
      <div className="bg-[#f5f5f5] px-3 py-1 rounded-full text-sm">{stretch.duration}秒</div>
    </div>
  )
}

function Search(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  )
}
