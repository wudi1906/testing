import type { SuggestionItem } from '.';
import React from 'react';
/**
 * Since Cascader not support ref active, we use `value` to mock the active item.
 */
export default function useActive(items: SuggestionItem[], open: boolean, rtl: boolean, onSelect: (value: string[]) => void, onCancel: () => void): readonly [string[], React.KeyboardEventHandler<Element>];
