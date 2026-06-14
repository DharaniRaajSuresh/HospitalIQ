import React, { useEffect, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

export default function AnimatedCounter({ value, formatter }) {
  // Parse numeric value
  let numericValue = null;
  let prefix = '';
  let suffix = '';

  if (typeof value === 'number') {
    numericValue = value;
  } else if (typeof value === 'string') {
    // try to extract the number if it has symbols like % or M or $
    const match = value.match(/^([^\d-]*)([\d,.]+)([^\d]*)$/);
    if (match) {
      prefix = match[1];
      numericValue = parseFloat(match[2].replace(/,/g, ''));
      suffix = match[3];
    }
  }

  if (numericValue === null || isNaN(numericValue)) {
    return <span>{formatter ? formatter(value) : value}</span>;
  }

  const spring = useSpring(0, {
    stiffness: 70,
    damping: 25,
    restDelta: 0.001
  });

  const [hasStarted, setHasStarted] = useState(false);

  useEffect(() => {
    spring.set(numericValue);
    setHasStarted(true);
  }, [numericValue, spring]);

  const display = useTransform(spring, (current) => {
    if (!hasStarted) {
      const init = formatter ? formatter(0) : "0";
      return `${prefix}${init}${suffix}`;
    }
    // Only round if the original didn't have decimal points unless it's small
    const isFloat = numericValue % 1 !== 0;
    const rounded = isFloat ? current.toFixed(1) : Math.round(current);
    const formatted = formatter ? formatter(rounded) : Number(rounded).toLocaleString();
    return `${prefix}${formatted}${suffix}`;
  });

  return <motion.span>{display}</motion.span>;
}
