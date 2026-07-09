import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { usePolling } from "./usePolling";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("usePolling", () => {
  it("starts in a loading state and populates data after the first fetch", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 1 });

    const { result } = renderHook(() => usePolling(fetcher, 10000));

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data).toEqual({ value: 1 });
    expect(result.current.error).toBeNull();
  });

  it("surfaces a fetch failure via `error` without clearing previous data", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ value: 1 })
      .mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => usePolling(fetcher, 5));

    await waitFor(() => expect(result.current.data).toEqual({ value: 1 }));

    await waitFor(() => expect(result.current.error).not.toBeNull());

    // stale data must remain visible instead of being reset to null
    expect(result.current.data).toEqual({ value: 1 });
  });

  it("refresh() triggers an immediate additional fetch", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 1 });

    const { result } = renderHook(() => usePolling(fetcher, 100000));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const callsBefore = fetcher.mock.calls.length;

    await act(async () => {
      await result.current.refresh();
    });

    expect(fetcher.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  it("stops polling after unmount", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 1 });

    const { result, unmount } = renderHook(() => usePolling(fetcher, 5));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    unmount();

    const callsAtUnmount = fetcher.mock.calls.length;

    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(fetcher.mock.calls.length).toBe(callsAtUnmount);
  });
});
