describe('Smoke Test', () => {
  it('should pass basic arithmetic', () => {
    expect(1 + 1).toBe(2);
  });

  it('should pass string comparison', () => {
    expect('hello').toBe('hello');
  });

  it('should pass array operations', () => {
    const arr = [1, 2, 3];
    expect(arr).toHaveLength(3);
    expect(arr).toContain(2);
  });

  it('should pass object operations', () => {
    const obj = { name: 'test', value: 123 };
    expect(obj).toHaveProperty('name', 'test');
    expect(obj.value).toBeGreaterThan(100);
  });
});