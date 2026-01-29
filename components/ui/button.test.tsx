import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Button } from "./button"

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole("button", { name: /click me/i })).toBeInTheDocument()
  })

  it("applies variant classes when variant is passed", () => {
    const { container } = render(<Button variant="destructive">Delete</Button>)
    const btn = container.querySelector("button")
    expect(btn).toBeInTheDocument()
  })
})
