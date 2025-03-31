#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(main);

typedef struct
{
    const struct gpio_dt_spec *button;
    const struct gpio_dt_spec *led;
    struct gpio_callback callback;
} button_led_t;

static const struct gpio_dt_spec button0 = GPIO_DT_SPEC_GET(DT_ALIAS(button0), gpios);
static const struct gpio_dt_spec button1 = GPIO_DT_SPEC_GET(DT_ALIAS(button1), gpios);
static const struct gpio_dt_spec button2 = GPIO_DT_SPEC_GET(DT_ALIAS(button2), gpios);
static const struct gpio_dt_spec led0 = GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios);
static const struct gpio_dt_spec led1 = GPIO_DT_SPEC_GET(DT_ALIAS(led1), gpios);
static const struct gpio_dt_spec led2 = GPIO_DT_SPEC_GET(DT_ALIAS(led2), gpios);

static button_led_t button_leds[] = {
    { &button0, &led0, },
    { &button1, &led1, },
    { &button2, &led2, },
};

static void button_pressed(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
    button_led_t *button_led = CONTAINER_OF(cb, button_led_t, callback);
    const struct gpio_dt_spec *led = button_led->led;
    gpio_pin_toggle_dt(led);
    printk("button %s pressed at %u \n", dev->name, k_cycle_get_32());
}

int main(void)
{
    for (int i = 0; i < ARRAY_SIZE(button_leds); i++)
    {
        button_led_t *button_led = &button_leds[i];
        const struct gpio_dt_spec *button = button_led->button;
        const struct gpio_dt_spec *led = button_led->led;
        if (!gpio_is_ready_dt(button) || !gpio_is_ready_dt(led))
        {
            LOG_ERR("button %s or led %s is not ready\n", button->port->name, led->port->name);
            return -ENODEV;
        }
    }

    for (int i = 0; i < ARRAY_SIZE(button_leds); i++)
    {
        int ret;
        button_led_t *button_led = &button_leds[i];
        const struct gpio_dt_spec *button = button_led->button;
        const struct gpio_dt_spec *led = button_led->led;
        ret = gpio_pin_configure_dt(led, GPIO_OUTPUT_INACTIVE);
        if (ret < 0)
        {
            LOG_ERR("led %s configure error %d\n", led->port->name, ret);
            return -EIO;
        }
        ret = gpio_pin_configure_dt(button, GPIO_INPUT);
        if (ret < 0)
        {
            LOG_ERR("button %s configure error %d\n", button->port->name, ret);
            return -EIO;
        }
        ret = gpio_pin_interrupt_configure_dt(button, GPIO_INT_EDGE_TO_ACTIVE);
        if (ret < 0)
        {
            LOG_ERR("button %s interrupt configure error %d\n", button->port->name, ret);
            return -EIO;
        }
        gpio_init_callback(&button_led->callback, button_pressed, BIT(button->pin));
        gpio_add_callback(button->port, &button_led->callback);
    }

    printk("ready\n");

    while (1)
    {
        k_msleep(1);
    }

    return 0;
}
