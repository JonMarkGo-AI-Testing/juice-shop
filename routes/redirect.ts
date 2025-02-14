/*
 * Copyright (c) 2014-2024 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import utils = require('../lib/utils')
import challengeUtils = require('../lib/challengeUtils')
import { type Request, type Response, type NextFunction } from 'express'
import { challenges } from '../data/datacache'

const security = require('../lib/insecurity')

const ALLOWED_REDIRECTS = {
  'dash': 'https://explorer.dash.org/address/Xr556RzuwX6hg5EGpkybbv5RanJoZN17kW',
  'btc': 'https://blockchain.info/address/1AbKfgvw9psQ41NbLi8kufDQTezwG8DRZm',
  'eth': 'https://etherscan.io/address/0x0f933ab9fcaaa782d0279c300d73750e1311eae6'
} as const

module.exports = function performRedirect () {
  return ({ query }: Request, res: Response, next: NextFunction) => {
    const redirectId = query.to as string
    const targetUrl = ALLOWED_REDIRECTS[redirectId as keyof typeof ALLOWED_REDIRECTS]

    if (!targetUrl) {
      res.status(406)
      next(new Error('Invalid redirect identifier'))
      return
    }

    if (!security.isRedirectAllowed(targetUrl)) {
      res.status(406)
      next(new Error('Redirect not allowed'))
      return
    }

    challengeUtils.solveIf(challenges.redirectCryptoCurrencyChallenge, () => {
      return Object.values(ALLOWED_REDIRECTS).includes(targetUrl)
    })
    challengeUtils.solveIf(challenges.redirectChallenge, () => {
      return !security.redirectAllowlist.some(allowedUrl => utils.startsWith(targetUrl, allowedUrl))
    })

    res.redirect(targetUrl)
  }
}
