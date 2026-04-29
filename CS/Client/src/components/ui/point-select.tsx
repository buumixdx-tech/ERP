import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

export interface PointOption {
  id: number
  name: string
  owner_name?: string
  owner_type?: string
  type: string
}

interface PointSelectProps {
  value: string
  onValueChange: (value: string) => void
  options: PointOption[]
  placeholder?: string
  className?: string
}

export function PointSelect({
  value,
  onValueChange,
  options,
  placeholder = "选择点位",
  className
}: PointSelectProps) {
  const [open, setOpen] = React.useState(false)

  const selectedOption = options.find(p => String(p.id) === value)

  const getDisplayText = (option: PointOption) => {
    return option.name
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
        >
          <span className={cn("truncate flex-1 text-left", !selectedOption && "text-muted-foreground")}>
            {selectedOption ? getDisplayText(selectedOption) : placeholder}
          </span>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-96 p-0" align="start">
        <div className="p-2">
          <div className="text-xs text-muted-foreground mb-2 px-2">
            {selectedOption ? `已选: ${getDisplayText(selectedOption)}` : `共 ${options.length} 个选项`}
          </div>
          <div className="max-h-[280px] overflow-y-auto space-y-1 p-1">
            {options.map(p => (
              <button
                key={p.id}
                type="button"
                onClick={() => {
                  onValueChange(String(p.id))
                  setOpen(false)
                }}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-md text-sm transition-colors",
                  "hover:bg-accent hover:text-accent-foreground",
                  String(p.id) === value && "bg-accent"
                )}
              >
                <div className="font-medium">{p.name}</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {p.owner_name || '闪饮'}{!p.owner_type ? '(自己)' : `(${p.owner_type})`} | {p.type}
                </div>
              </button>
            ))}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
