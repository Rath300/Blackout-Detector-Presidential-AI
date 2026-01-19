import { cn } from "@/lib/utils"
import React, { useRef, useState } from "react"
import { motion } from "framer-motion"
import { Upload } from "lucide-react"
import { useDropzone } from "react-dropzone"

const mainVariant = {
  initial: {
    x: 0,
    y: 0,
  },
  animate: {
    x: 16,
    y: -16,
    opacity: 0.9,
  },
}

const secondaryVariant = {
  initial: {
    opacity: 0,
  },
  animate: {
    opacity: 1,
  },
}

export const FileUpload = ({
  onChange,
}: {
  onChange?: (files: File[]) => void
}) => {
  const [files, setFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (newFiles: File[]) => {
    setFiles((prevFiles) => [...prevFiles, ...newFiles])
    onChange && onChange(newFiles)
  }

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  const { getRootProps, isDragActive } = useDropzone({
    multiple: false,
    noClick: true,
    onDrop: handleFileChange,
    onDropRejected: (error) => {
      console.log(error)
    },
  })

  return (
    <div className="w-full" {...getRootProps()}>
      <motion.div
        onClick={handleClick}
        whileHover="animate"
        className="p-8 group/file block rounded-lg cursor-pointer w-full relative overflow-hidden border border-emerald-100 bg-white"
      >
        <input
          ref={fileInputRef}
          id="file-upload-handle"
          type="file"
          onChange={(e) => handleFileChange(Array.from(e.target.files || []))}
          className="hidden"
        />
        <div className="absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,white,transparent)]">
          <GridPattern />
        </div>
        <div className="flex flex-col items-center justify-center">
          <p className="relative z-20 font-medium text-emerald-700 text-base">
            Upload inverter CSV
          </p>
          <p className="relative z-20 font-normal text-slate-500 text-sm mt-2">
            Drag or drop a file, or click to choose one
          </p>
          <div className="relative w-full mt-8 max-w-xl mx-auto">
            {files.length > 0 &&
              files.map((file, idx) => (
                <motion.div
                  key={"file" + idx}
                  layoutId={idx === 0 ? "file-upload" : "file-upload-" + idx}
                  className={cn(
                    "relative overflow-hidden z-40 bg-white flex flex-col items-start justify-start md:h-24 p-4 mt-4 w-full mx-auto rounded-md border border-emerald-100",
                    "shadow-sm"
                  )}
                >
                  <div className="flex justify-between w-full items-center gap-4">
                    <motion.p
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      layout
                      className="text-sm text-slate-700 truncate max-w-xs"
                    >
                      {file.name}
                    </motion.p>
                    <motion.p
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      layout
                      className="rounded-lg px-2 py-1 w-fit flex-shrink-0 text-xs text-emerald-700 bg-emerald-50"
                    >
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </motion.p>
                  </div>

                  <div className="flex text-xs md:flex-row flex-col items-start md:items-center w-full mt-2 justify-between text-slate-500">
                    <motion.p
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      layout
                      className="px-1 py-0.5 rounded-md bg-emerald-50"
                    >
                      {file.type || "text/csv"}
                    </motion.p>

                    <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} layout>
                      modified {new Date(file.lastModified).toLocaleDateString()}
                    </motion.p>
                  </div>
                </motion.div>
              ))}
            {!files.length && (
              <motion.div
                layoutId="file-upload"
                variants={mainVariant}
                transition={{
                  type: "spring",
                  stiffness: 300,
                  damping: 20,
                }}
                className={cn(
                  "relative group-hover/file:shadow-2xl z-40 bg-white flex items-center justify-center h-28 mt-4 w-full max-w-[7rem] mx-auto rounded-md border border-emerald-100",
                  "shadow-[0px_10px_40px_rgba(16,185,129,0.08)]"
                )}
              >
                {isDragActive ? (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-emerald-700 flex flex-col items-center text-xs"
                  >
                    Drop it
                    <Upload className="h-4 w-4 text-emerald-600" />
                  </motion.p>
                ) : (
                  <Upload className="h-4 w-4 text-emerald-600" />
                )}
              </motion.div>
            )}

            {!files.length && (
              <motion.div
                variants={secondaryVariant}
                className="absolute opacity-0 border border-dashed border-emerald-200 inset-0 z-30 bg-transparent flex items-center justify-center h-28 mt-4 w-full max-w-[7rem] mx-auto rounded-md"
              ></motion.div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export function GridPattern() {
  const columns = 20
  const rows = 6
  return (
    <div className="flex bg-emerald-50 flex-shrink-0 flex-wrap justify-center items-center gap-x-px gap-y-px scale-105">
      {Array.from({ length: rows }).map((_, row) =>
        Array.from({ length: columns }).map((_, col) => {
          const index = row * columns + col
          return (
            <div
              key={`${col}-${row}`}
              className={`w-10 h-10 flex flex-shrink-0 rounded-[2px] ${
                index % 2 === 0
                  ? "bg-emerald-50"
                  : "bg-emerald-100/60 shadow-[0px_0px_1px_2px_rgba(255,255,255,0.8)_inset]"
              }`}
            />
          )
        })
      )}
    </div>
  )
}
